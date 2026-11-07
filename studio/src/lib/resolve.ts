// Chuẩn hoá element: điền giá trị mặc định theo style, tính hình học (box, đầu bút).
import type {
	EnterType,
	ExitType,
	FontKind,
	ImageSizes,
	Scene,
	TraceData,
	TraceMap,
	Style,
	TextElement,
	TimelineElement,
	Vec,
} from '../types';
import {resolveAsset} from './assets';
import {formatVi} from './format';
import {clamp, makePolyline, pointAtLength, seededRandom, type Polyline} from './math';
import {getPathInfo} from './path-metrics';
import {getScribble} from './scribble';
import {HAND_JITTER_PX, tracePointAt} from './trace';
import {layoutText, measureWidth, type TextLayout} from './text-layout';
import {fitBlocks, type FittedBlock} from './fit-text';
import {
	DEFAULT_BOWING,
	DEFAULT_ROUGHNESS,
	roughEllipse,
	roughPath,
	roughPointAt,
	roughRect,
	type RoughConfig,
	type RoughDrawing,
} from './rough';

export interface Ctx {
	videoId: string;
	style: Style;
	fps: number;
	imageSizes: ImageSizes;
	defaultFont: FontKind;
	traces: TraceMap;
	/** timeline.rough/roughness/bowing; bỏ trống = tắt (nét hình học như cũ) */
	rough?: {enabled: boolean; roughness: number; bowing: number};
	/** timeline.fitText; bỏ trống = tắt */
	fitText?: boolean;
}

/** Cấu hình nét vẽ tay cho element (element.rough ghi đè timeline.rough); null = nét hình học như cũ */
const roughCfgOf = (el: {rough?: boolean}, ctx: Ctx): RoughConfig | null => {
	const on = el.rough ?? ctx.rough?.enabled ?? false;
	if (!on) return null;
	return {
		roughness: ctx.rough?.roughness ?? DEFAULT_ROUGHNESS,
		bowing: ctx.rough?.bowing ?? DEFAULT_BOWING,
	};
};

/** element.fit ghi đè timeline.fitText */
const fitOn = (el: {fit?: boolean}, ctx: Ctx) => el.fit ?? ctx.fitText ?? false;

/** padding chữ trong rect/circle (khớp ShapeView) */
export const SHAPE_LABEL_PAD = 12;
/** padding / khoảng cách trong card (khớp CardView) */
export const CARD_PAD = 24;
export const CARD_GAP = 12;

export interface Box {
	/** góc trên-trái của box so với điểm neo (x,y) */
	ox: number;
	oy: number;
	w: number;
	h: number;
}

export interface Geometry {
	box: Box;
	/** điểm neo (toạ độ scene) trước khi áp moves */
	anchor: Vec;
	/** vị trí đầu bút (local, so với neo) theo tiến độ vẽ 0..1 */
	tipAt: (p: number) => Vec;
	text?: TextLayout & {pad: {x: number; y: number}; size: number};
	/** rect/circle: label đã co cho vừa khung (chỉ khi fit) */
	label?: FittedBlock;
	/** card: title/body đã co cho vừa thẻ (chỉ khi fit) */
	cardText?: {title?: FittedBlock; body?: FittedBlock};
	/** nét vẽ tay rough.js (rect/circle: toạ độ local; path: toạ độ như el.d) */
	rough?: RoughDrawing;
	outline?: Polyline;
	scribble?: ReturnType<typeof getScribble>;
	imageSize?: {w: number; h: number};
	/** trace map (nếu image.trace và dữ liệu đã nạp) */
	trace?: TraceData;
	path?: ReturnType<typeof getPathInfo>;
}

export interface Resolved<E extends TimelineElement = TimelineElement> {
	el: E;
	font: FontKind;
	enterAt: number;
	enter: EnterType;
	enterDur: number;
	hand: boolean;
	exitAt: number | null;
	exit: ExitType;
	exitDur: number;
	geom: Geometry;
}

const DRAWABLE_DEFAULT_C = true;

export const textBoxPad = (el: TextElement, size: number) => {
	if (!el.box || el.box === 'none') return {x: 0, y: 0};
	if (el.box === 'pill') return {x: size * 0.6, y: size * 0.28};
	return {x: size * 0.55, y: size * 0.4};
};

const wipeTip = (box: Box) => (p: number): Vec => {
	const osc = Math.max(2, Math.round(box.w / 110));
	return {
		x: box.ox + p * box.w,
		y: box.oy + box.h * (0.5 + 0.38 * Math.sin(p * Math.PI * 2 * osc)),
	};
};

const rectOutline = (w: number, h: number, r: number): Polyline => {
	const rr = clamp(r, 0, Math.min(w, h) / 2);
	const pts: Vec[] = [];
	const x0 = -w / 2;
	const y0 = -h / 2;
	const arc = (cx: number, cy: number, a0: number) => {
		for (let i = 0; i <= 6; i++) {
			const a = a0 + (Math.PI / 2) * (i / 6);
			pts.push({x: cx + rr * Math.cos(a), y: cy + rr * Math.sin(a)});
		}
	};
	// bắt đầu từ góc trên-trái, đi theo chiều kim đồng hồ
	pts.push({x: x0 + rr, y: y0});
	pts.push({x: x0 + w - rr, y: y0});
	arc(x0 + w - rr, y0 + rr, -Math.PI / 2);
	pts.push({x: x0 + w, y: y0 + h - rr});
	arc(x0 + w - rr, y0 + h - rr, 0);
	pts.push({x: x0 + rr, y: y0 + h});
	arc(x0 + rr, y0 + h - rr, Math.PI / 2);
	pts.push({x: x0, y: y0 + rr});
	arc(x0 + rr, y0 + rr, Math.PI);
	return makePolyline(pts);
};

const circleOutline = (r: number): Polyline => {
	const pts: Vec[] = [];
	const n = 72;
	for (let i = 0; i <= n; i++) {
		const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
		pts.push({x: r * Math.cos(a), y: r * Math.sin(a)});
	}
	return makePolyline(pts);
};

export const imageSizeOf = (
	ctx: Ctx,
	src: string,
	w: number,
	h?: number,
): {w: number; h: number} => {
	if (h) return {w, h};
	const nat = ctx.imageSizes[resolveAsset(ctx.videoId, src)];
	if (nat && nat.w > 0) return {w, h: (w * nat.h) / nat.w};
	return {w, h: w};
};

const counterText = (el: Extract<TimelineElement, {type: 'counter'}>, v: number) =>
	`${el.prefix ?? ''}${formatVi(v, el.decimals ?? 0, el.thousands ?? true)}${el.suffix ?? ''}`;
export {counterText};

const computeGeometry = (el: TimelineElement, font: FontKind, ctx: Ctx): Geometry => {
	const x = el.x ?? 0;
	const y = el.y ?? 0;
	const center = (w: number, h: number): Box => ({ox: -w / 2, oy: -h / 2, w, h});
	switch (el.type) {
		case 'image': {
			const size = imageSizeOf(ctx, el.src, el.w, el.h);
			const box = center(size.w, size.h);
			const sc = getScribble(size.w, size.h, el.id);
			const trace = el.trace ? ctx.traces[resolveAsset(ctx.videoId, el.src)] : undefined;
			if (trace) {
				const kx = size.w / trace.width;
				const ky = size.h / trace.height;
				// rung tay theo px scene; pha riêng cho mỗi element (xác định theo id)
				const jitter = {amp: HAND_JITTER_PX, pxScale: (kx + ky) / 2, seed: seededRandom(el.id)() * Math.PI * 2};
				return {
					box,
					anchor: {x, y},
					imageSize: size,
					scribble: sc,
					trace,
					tipAt: (p) => {
						const q = tracePointAt(trace, p, jitter);
						const px = el.flipX ? trace.width - q.x : q.x;
						return {x: px * kx + box.ox, y: q.y * ky + box.oy};
					},
				};
			}
			return {
				box,
				anchor: {x, y},
				imageSize: size,
				scribble: sc,
				tipAt: (p) => {
					// làm mượt: trung bình vài điểm gần đầu nét → tay bớt giật
					const L = sc.poly.length * p;
					let sx = 0;
					let sy = 0;
					const K = 5;
					for (let i = 0; i < K; i++) {
						const q = pointAtLength(sc.poly, L - (sc.zig * 1.5 * i) / (K - 1));
						sx += q.x;
						sy += q.y;
					}
					return {x: sx / K + box.ox, y: sy / K + box.oy};
				},
			};
		}
		case 'text': {
			const weight = el.weight ?? 600;
			const lh = el.lineHeight ?? 1.25;
			let size = el.size ?? 56;
			if (el.maxWidth && fitOn(el, ctx)) {
				const fit = fitBlocks([{text: el.text, size, weight, lineHeight: lh}], font, el.maxWidth, Infinity, 0, el.maxLines ?? 2);
				size = fit.blocks[0].size;
			}
			const lay = layoutText(el.text, size, weight, font, el.maxWidth, lh);
			const pad = textBoxPad(el, size);
			const w = lay.width + pad.x * 2;
			const h = lay.height + pad.y * 2;
			const align = el.align ?? 'center';
			const box: Box = {
				ox: align === 'left' ? 0 : align === 'right' ? -w : -w / 2,
				oy: -h / 2,
				w,
				h,
			};
			const total = lay.lines.reduce((s, l) => s + Math.max(l.width, 1), 0);
			// T4: khoanh/gạch chân bằng rough.js quanh cả khối chữ (rough-notation kiểu tối giản, không thêm thư viện ngoài)
			let mark: RoughDrawing | undefined;
			const markRc = el.mark ? roughCfgOf(el, ctx) : null;
			if (markRc) {
				const sw = el.markWidth ?? 5;
				mark =
					el.mark === 'khoanh'
						? roughEllipse(`${el.id}-mark`, w * 1.22, h * 1.75, sw, markRc)
						: roughPath(`${el.id}-mark`, `M${-w * 0.47} ${h / 2 + 10} L${w * 0.47} ${h / 2 + 6}`, sw, markRc, null);
			}
			return {
				box,
				anchor: {x, y},
				text: {...lay, pad, size},
				rough: mark,
				tipAt: (p) => {
					let acc = p * total;
					for (let i = 0; i < lay.lines.length; i++) {
						const lw = Math.max(lay.lines[i].width, 1);
						if (acc <= lw || i === lay.lines.length - 1) {
							const lx = lineLeft(lay, i, w, pad.x, align);
							const cx = lx + Math.min(acc, lw);
							return {
								x: box.ox + cx,
								y:
									box.oy +
									pad.y +
									lay.lineHeight * (i + 0.72) +
									Math.sin(cx / (size * 0.18)) * size * 0.07,
							};
						}
						acc -= lw;
					}
					return {x: 0, y: 0};
				},
			};
		}
		case 'counter': {
			const size = el.size ?? 96;
			const weight = el.weight ?? 800;
			const w = Math.max(
				measureWidth(counterText(el, el.from), size, weight, font),
				measureWidth(counterText(el, el.to), size, weight, font),
			);
			const box = center(w * 1.04, size * 1.2);
			return {box, anchor: {x, y}, tipAt: wipeTip(box)};
		}
		case 'card': {
			const box = center(el.w, el.h);
			const rc = roughCfgOf(el, ctx);
			const sw = ctx.style === 'C' ? 3 : 2;
			const dr = rc ? roughRect(el.id, el.w, el.h, el.radius ?? 20, sw, rc) : undefined;
			if (!fitOn(el, ctx) || !(el.title || el.body)) return {box, anchor: {x, y}, tipAt: wipeTip(box), rough: dr};
			// vùng chữ = thẻ trừ padding, trừ icon (maxHeight 38% / maxWidth 60%, giữ tỉ lệ) + gap
			let iconH = 0;
			if (el.icon) {
				const nat = ctx.imageSizes[resolveAsset(ctx.videoId, el.icon)];
				iconH =
					nat && nat.w > 0 && nat.h > 0
						? nat.h * Math.min(1, (el.w * 0.6) / nat.w, (el.h * 0.38) / nat.h)
						: el.h * 0.38;
				iconH += CARD_GAP;
			}
			const blocks = [
				...(el.title ? [{text: el.title, size: el.titleSize ?? 36, weight: 800, lineHeight: 1.2}] : []),
				...(el.body ? [{text: el.body, size: el.bodySize ?? 24, weight: 400, lineHeight: 1.35}] : []),
			];
			const fit = fitBlocks(blocks, font, el.w - CARD_PAD * 2, el.h - CARD_PAD * 2 - iconH, CARD_GAP);
			return {
				box,
				anchor: {x, y},
				tipAt: wipeTip(box),
				rough: dr,
				cardText: {
					title: el.title ? fit.blocks[0] : undefined,
					body: el.body ? fit.blocks[el.title ? 1 : 0] : undefined,
				},
			};
		}
		case 'bar': {
			// ngang: box = cả rãnh, tâm tại (x,y) — khớp BarView (dùng cho zoom-from và nét "lau" khi draw)
			if (el.horizontal) {
				const box = center(el.w, Math.max(1, el.maxH));
				return {box, anchor: {x, y}, tipAt: wipeTip(box)};
			}
			const h =Math.max(1, el.maxH * clamp(el.value, 0, 1));
			const box: Box = {ox: -el.w / 2, oy: -h, w: el.w, h};
			return {box, anchor: {x, y}, tipAt: wipeTip(box)};
		}
		case 'path': {
			const info = getPathInfo(el.d);
			const c = {x: info.bbox.x + info.bbox.w / 2, y: info.bbox.y + info.bbox.h / 2};
			const box = center(Math.max(info.bbox.w, 1), Math.max(info.bbox.h, 1));
			const rc = roughCfgOf(el, ctx);
			if (rc && info.length > 0) {
				const sw = el.strokeWidth ?? 6;
				let head = null;
				if (el.arrow) {
					const size = Math.max(14, sw * 4.5);
					const tip = info.pointAt(info.length);
					const back = info.pointAt(Math.max(0, info.length - Math.min(size, info.length * 0.5)));
					head = {tip, angle: Math.atan2(tip.y - back.y, tip.x - back.x), size};
				}
				const dr = roughPath(el.id, el.d, sw, rc, head);
				return {
					box,
					anchor: {x: c.x + x, y: c.y + y},
					path: info,
					rough: dr,
					tipAt: (p) => {
						const q = roughPointAt(dr, p);
						return {x: q.x - c.x, y: q.y - c.y};
					},
				};
			}
			return {
				box,
				// path dùng toạ độ tuyệt đối; x/y (nếu có) là độ lệch
				anchor: {x: c.x + x, y: c.y + y},
				path: info,
				tipAt: (p) => {
					const q = info.pointAt(info.length * p);
					return {x: q.x - c.x, y: q.y - c.y};
				},
			};
		}
		case 'rect':
		case 'circle': {
			const w = el.type === 'circle' ? (el.r ? el.r * 2 : (el.w ?? 160)) : (el.w ?? 240);
			const h = el.type === 'circle' ? w : (el.h ?? 140);
			const outline =
				el.type === 'circle' ? circleOutline(w / 2) : rectOutline(w, h, el.radius ?? 16);
			let label: FittedBlock | undefined;
			if (el.label && fitOn(el, ctx)) {
				// circle: chữ nằm trong hình vuông nội tiếp để không lòi ra ngoài viền tròn
				const iw = el.type === 'circle' ? w * Math.SQRT1_2 : w;
				const ih = el.type === 'circle' ? h * Math.SQRT1_2 : h;
				label = fitBlocks(
					[{text: el.label, size: el.labelSize ?? 32, weight: el.labelWeight ?? 600, lineHeight: 1.2}],
					font,
					iw - SHAPE_LABEL_PAD * 2,
					ih - SHAPE_LABEL_PAD * 2,
				).blocks[0];
			}
			const rc = roughCfgOf(el, ctx);
			if (rc) {
				const sw = el.strokeWidth ?? (el.stroke ? 4 : 5);
				const dr =
					el.type === 'circle'
						? roughEllipse(el.id, w, h, sw, rc)
						: roughRect(el.id, w, h, el.radius ?? 16, sw, rc);
				return {
					box: center(w, h),
					anchor: {x, y},
					outline,
					label,
					rough: dr,
					tipAt: (p) => roughPointAt(dr, p),
				};
			}
			return {
				box: center(w, h),
				anchor: {x, y},
				outline,
				label,
				tipAt: (p) => pointAtLength(outline, outline.length * p),
			};
		}
		case 'clock': {
			const outline = circleOutline(el.r);
			return {
				box: center(el.r * 2, el.r * 2),
				anchor: {x, y},
				outline,
				tipAt: (p) => pointAtLength(outline, outline.length * p),
			};
		}
		case 'caption': {
			// Bố cục chữ nhiều dòng tự co giãn theo CSS (flex-wrap), không đo trước như text/card —
			// chỉ cần box danh nghĩa để camera/finish() có toạ độ tham chiếu.
			const w = el.maxWidth ?? 900;
			return {box: center(w, 160), anchor: {x, y}, tipAt: wipeTip(center(w, 160))};
		}
	}
};

export const lineLeft = (
	lay: TextLayout,
	i: number,
	blockW: number,
	padX: number,
	align: 'left' | 'center' | 'right',
) => {
	const lw = lay.lines[i].width;
	if (align === 'left') return padX;
	if (align === 'right') return blockW - padX - lw;
	return (blockW - lw) / 2;
};

const defaultDrawDuration = (el: TimelineElement, g: Geometry): number => {
	switch (el.type) {
		case 'image':
			return clamp(0.9 + (g.box.w * g.box.h) / 350000, 0.9, 2.4);
		case 'text':
			return clamp(el.text.length * 0.05, 0.5, 2.6);
		case 'path':
			return clamp((g.path?.length ?? 600) / 900, 0.5, 2);
		default:
			return 0.9;
	}
};

export const resolveElement = (
	el: TimelineElement,
	scene: Scene,
	ctx: Ctx,
): Resolved => {
	const isC = ctx.style === 'C';
	const font: FontKind =
		('font' in el && el.font) || ctx.defaultFont;
	const enter: EnterType =
		el.enter ??
		(isC && DRAWABLE_DEFAULT_C
			? 'draw'
			: el.type === 'bar'
				? 'grow'
				: el.type === 'path'
					? 'draw'
					: 'fade');
	// Style A: không bao giờ hiện tay. Style C: mặc định có tay.
	const hand =
		enter === 'draw' &&
		(ctx.style === 'A' ? false : (el.hand ?? (isC ? true : false)));
	const geom = computeGeometry(el, font, ctx);
	const defaultDur =
		enter === 'draw'
			? defaultDrawDuration(el, geom)
			: enter === 'fade'
				? 0.4
				: 0.5;
	return {
		el,
		font,
		enterAt: el.enterAt ?? scene.start,
		enter,
		enterDur: Math.max(0, el.enterDuration ?? defaultDur),
		hand,
		exitAt: el.exitAt ?? null,
		exit: el.exit ?? 'fade',
		exitDur: Math.max(0, el.exitDuration ?? 0.3),
		geom,
	};
};
