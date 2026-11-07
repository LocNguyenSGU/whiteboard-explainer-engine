// Nét "vẽ tay" (rough) cho rect / circle / path bằng rough.js (MIT, https://roughjs.com).
// Sinh path SVG MỘT lần mỗi element (cache theo id + hình học + tham số), seed xác định theo id
// → mọi frame / mọi lần render ra y hệt nhau.
import rough from 'roughjs';
import type {Op, Options} from 'roughjs/bin/core';
import type {Vec} from '../types';
import {makePolyline, pointAtLength, seededRandom, type Polyline} from './math';

export interface RoughConfig {
	/** độ "run tay" của rough.js (0 = thẳng tắp). Mặc định 1.2 */
	roughness: number;
	/** độ cong võng của đoạn thẳng. Mặc định 1 */
	bowing: number;
}

export const DEFAULT_ROUGHNESS = 1.2;
export const DEFAULT_BOWING = 1;

/** Một nét bút: nét chính (tay đi theo) + nét đè thứ hai của rough.js (nếu có), lộ ra cùng nhịp */
export interface RoughStroke {
	d: string;
	/** nét đè (multi-stroke của rough.js); null nếu không có */
	d2: string | null;
	poly: Polyline;
	/** true = không áp nét đứt (vd. ngạnh mũi tên trên đường đứt) */
	solid: boolean;
}

export interface RoughDrawing {
	strokes: RoughStroke[];
	/** độ dài tích luỹ các nét chính (cum[i] = điểm bắt đầu nét i) */
	cum: number[];
	length: number;
}

const cache = new Map<string, RoughDrawing>();

/** seed rough.js phải là số nguyên ≠ 0 (0 = ngẫu nhiên) */
const seedOf = (id: string) => 1 + Math.floor(seededRandom(`rough|${id}`)() * 2147483000);

const f2 = (v: number) => v.toFixed(2);

/** Tách danh sách op của rough.js thành các nét con (mỗi 'move' mở một nét), bỏ nét rỗng */
const splitOps = (ops: Op[]): Op[][] => {
	const out: Op[][] = [];
	let cur: Op[] = [];
	for (const op of ops) {
		if (op.op === 'move') {
			if (cur.length > 1) out.push(cur);
			cur = [op];
		} else if (cur.length) {
			cur.push(op);
		}
	}
	if (cur.length > 1) out.push(cur);
	return out;
};

const opsToD = (ops: Op[]) =>
	ops
		.map((o) => {
			const d = o.data;
			if (o.op === 'move') return `M${f2(d[0])} ${f2(d[1])}`;
			if (o.op === 'lineTo') return `L${f2(d[0])} ${f2(d[1])}`;
			return `C${f2(d[0])} ${f2(d[1])} ${f2(d[2])} ${f2(d[3])} ${f2(d[4])} ${f2(d[5])}`;
		})
		.join(' ');

/** Làm phẳng nét con thành polyline để tính độ dài / vị trí đầu bút (không cần DOM) */
const opsToPoly = (ops: Op[]): Polyline => {
	const pts: Vec[] = [];
	let cx = 0;
	let cy = 0;
	for (const o of ops) {
		const d = o.data;
		if (o.op === 'move' || o.op === 'lineTo') {
			cx = d[0];
			cy = d[1];
			pts.push({x: cx, y: cy});
			continue;
		}
		const N = 12;
		for (let i = 1; i <= N; i++) {
			const t = i / N;
			const u = 1 - t;
			const a = u * u * u;
			const b = 3 * u * u * t;
			const c = 3 * u * t * t;
			const e = t * t * t;
			pts.push({x: a * cx + b * d[0] + c * d[2] + e * d[4], y: a * cy + b * d[1] + c * d[3] + e * d[5]});
		}
		cx = d[4];
		cy = d[5];
	}
	return makePolyline(pts);
};

/**
 * rough.js (multi-stroke) vẽ mỗi đoạn 2 lần liền nhau: [a1, b1, a2, b2, ...].
 * Ghép cặp → nét chính a_i (tay đi theo) + nét đè b_i lộ cùng nhịp. Số nét lẻ → không ghép.
 */
const toStrokes = (ops: Op[], solid: boolean): RoughStroke[] => {
	const subs = splitOps(ops);
	if (subs.length % 2 !== 0) {
		return subs.map((s) => ({d: opsToD(s), d2: null, poly: opsToPoly(s), solid}));
	}
	const out: RoughStroke[] = [];
	for (let i = 0; i < subs.length; i += 2) {
		out.push({d: opsToD(subs[i]), d2: opsToD(subs[i + 1]), poly: opsToPoly(subs[i]), solid});
	}
	return out;
};

const finish = (strokes: RoughStroke[]): RoughDrawing => {
	const cum: number[] = [];
	let acc = 0;
	for (const s of strokes) {
		cum.push(acc);
		acc += s.poly.length;
	}
	return {strokes, cum, length: acc};
};

const options = (id: string, cfg: RoughConfig, sw: number, salt = ''): Options => ({
	seed: seedOf(id + salt),
	roughness: cfg.roughness,
	bowing: cfg.bowing,
	strokeWidth: sw,
	stroke: '#000',
	fill: undefined,
});

const pathOps = (d: string, o: Options): Op[] =>
	rough
		.generator()
		.path(d, o)
		.sets.filter((s) => s.type === 'path')
		.flatMap((s) => s.ops);

const memo = (key: string, make: () => RoughDrawing): RoughDrawing => {
	const hit = cache.get(key);
	if (hit) return hit;
	const v = make();
	cache.set(key, v);
	return v;
};

const cfgKey = (cfg: RoughConfig, sw: number) => `${cfg.roughness}|${cfg.bowing}|${sw}`;

/** Hình chữ nhật (bo góc) toạ độ local, tâm (0,0), bắt đầu góc trên-trái, chiều kim đồng hồ */
export const roughRect = (id: string, w: number, h: number, radius: number, sw: number, cfg: RoughConfig) =>
	memo(`rect|${id}|${w}|${h}|${radius}|${cfgKey(cfg, sw)}`, () => {
		const rr = Math.max(0, Math.min(radius, Math.min(w, h) / 2));
		const x0 = -w / 2;
		const y0 = -h / 2;
		const x1 = x0 + w;
		const y1 = y0 + h;
		const d =
			rr > 0.5
				? `M${x0 + rr} ${y0} L${x1 - rr} ${y0} A${rr} ${rr} 0 0 1 ${x1} ${y0 + rr} L${x1} ${y1 - rr} ` +
					`A${rr} ${rr} 0 0 1 ${x1 - rr} ${y1} L${x0 + rr} ${y1} A${rr} ${rr} 0 0 1 ${x0} ${y1 - rr} ` +
					`L${x0} ${y0 + rr} A${rr} ${rr} 0 0 1 ${x0 + rr} ${y0}`
				: `M${x0} ${y0} L${x1} ${y0} L${x1} ${y1} L${x0} ${y1} L${x0} ${y0}`;
		return finish(toStrokes(pathOps(d, options(id, cfg, sw)), false));
	});

/** Ellipse toạ độ local, tâm (0,0) */
export const roughEllipse = (id: string, w: number, h: number, sw: number, cfg: RoughConfig) =>
	memo(`ellipse|${id}|${w}|${h}|${cfgKey(cfg, sw)}`, () => {
		const dr = rough.generator().ellipse(0, 0, w, h, options(id, cfg, sw));
		const ops = dr.sets.filter((s) => s.type === 'path').flatMap((s) => s.ops);
		return finish(toStrokes(ops, false));
	});

export interface ArrowHead {
	tip: Vec;
	/** góc hướng của nét tại đầu mũi tên (rad) */
	angle: number;
	/** độ dài mỗi ngạnh */
	size: number;
}

/** Ngạnh mũi tên dạng chữ V hở: một nét  ngạnh-trái → đỉnh → ngạnh-phải */
const SPREAD = 0.5;

/** Path tự do (toạ độ tuyệt đối như el.d) + ngạnh mũi tên (vẽ sau cùng) nếu có */
export const roughPath = (id: string, d: string, sw: number, cfg: RoughConfig, head: ArrowHead | null) =>
	memo(
		`path|${id}|${d}|${cfgKey(cfg, sw)}|${head ? `${f2(head.tip.x)},${f2(head.tip.y)},${head.angle.toFixed(4)},${head.size}` : ''}`,
		() => {
			const strokes = toStrokes(pathOps(d, options(id, cfg, sw)), false);
			if (head) {
				const {tip, angle, size} = head;
				const l = {x: tip.x + Math.cos(angle + Math.PI - SPREAD) * size, y: tip.y + Math.sin(angle + Math.PI - SPREAD) * size};
				const r = {x: tip.x + Math.cos(angle + Math.PI + SPREAD) * size, y: tip.y + Math.sin(angle + Math.PI + SPREAD) * size};
				// ngạnh ngắn: giảm độ run để đầu mũi tên gọn, vẫn khớp nét thân
				const o = options(id, {roughness: Math.min(cfg.roughness, 1), bowing: cfg.bowing * 0.5}, sw, '|head');
				const ops = rough
					.generator()
					.linearPath(
						[
							[l.x, l.y],
							[tip.x, tip.y],
							[r.x, r.y],
						],
						o,
					)
					.sets.filter((s) => s.type === 'path')
					.flatMap((s) => s.ops);
				strokes.push(...toStrokes(ops, true));
			}
			return finish(strokes);
		},
	);

/** Tỉ lệ lộ (0..1) của từng nét khi tiến độ vẽ = p: các nét lộ lần lượt theo độ dài */
export const revealFractions = (dr: RoughDrawing, p: number): number[] => {
	if (p >= 1) return dr.strokes.map(() => 1);
	const at = Math.max(0, p) * dr.length;
	return dr.strokes.map((s, i) => {
		const len = s.poly.length;
		if (len <= 0) return at >= dr.cum[i] ? 1 : 0;
		return Math.max(0, Math.min(1, (at - dr.cum[i]) / len));
	});
};

/** Vị trí đầu bút (cùng hệ toạ độ với path) tại tiến độ p */
export const roughPointAt = (dr: RoughDrawing, p: number): Vec => {
	if (!dr.strokes.length) return {x: 0, y: 0};
	const at = Math.max(0, Math.min(1, p)) * dr.length;
	let i = dr.strokes.length - 1;
	while (i > 0 && dr.cum[i] > at) i--;
	return pointAtLength(dr.strokes[i].poly, at - dr.cum[i]);
};
