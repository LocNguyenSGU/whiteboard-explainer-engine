// Trạng thái animation của 1 element tại thời điểm t (giây tuyệt đối). Hàm thuần.
import {spring} from 'remotion';
import type {Vec} from '../types';
import {clamp, easeDraw, easeIn, easeInOut, easeOut, lerp, progress} from './math';
import type {Resolved} from './resolve';

export interface ElementState {
	visible: boolean;
	/** điểm neo sau moves (toạ độ scene) */
	x: number;
	y: number;
	dx: number;
	dy: number;
	scale: number;
	rotate: number;
	rotateY: number;
	opacity: number;
	/** tiến độ vẽ 0..1 khi enter = draw, null nếu không vẽ */
	draw: number | null;
	grayscale: number;
}

const SLIDE = 60;

// Spring êm: overshoot rất nhỏ (<4% trên khoảng 0.85→1)
const POP_SPRING = {damping: 18, stiffness: 180, mass: 1};

export const computeState = (r: Resolved, t: number, fps: number): ElementState => {
	const {el, geom} = r;
	const s: ElementState = {
		visible: true,
		x: geom.anchor.x,
		y: geom.anchor.y,
		dx: 0,
		dy: 0,
		scale: el.scale ?? 1,
		rotate: el.rotate ?? 0,
		rotateY: 0,
		opacity: el.opacity ?? 1,
		draw: null,
		grayscale: 0,
	};

	// --- moves (tích luỹ, easeInOut) ---
	if (el.moves && el.moves.length) {
		const ms = [...el.moves].sort((a, b) => a.at - b.at);
		const isPath = el.type === 'path';
		for (const m of ms) {
			if (t < m.at) break;
			const p = easeInOut(progress(t, m.at, m.duration ?? 0.6));
			// path: x/y của move là độ lệch so với vị trí gốc
			if (m.x !== undefined) s.x = lerp(s.x, isPath ? geom.anchor.x + m.x : m.x, p);
			if (m.y !== undefined) s.y = lerp(s.y, isPath ? geom.anchor.y + m.y : m.y, p);
			if (m.scale !== undefined) s.scale = lerp(s.scale, m.scale, p);
			if (m.rotate !== undefined) s.rotate = lerp(s.rotate, m.rotate, p);
			if (m.opacity !== undefined) s.opacity = lerp(s.opacity, m.opacity, p);
		}
	}

	// --- enter ---
	if (t < r.enterAt) {
		s.visible = false;
		return s;
	}
	const e = t - r.enterAt;
	const p = progress(t, r.enterAt, r.enterDur);
	const flip = el.type === 'card' && el.flipIn;
	if (flip) {
		s.rotateY = 90 * (1 - easeOut(p));
		s.opacity *= clamp(p * 4, 0, 1);
		if (r.enter === 'pop') s.scale *= 0.92 + 0.08 * easeOut(p);
	} else {
		switch (r.enter) {
			case 'pop': {
				const sp = spring({
					frame: e * fps,
					fps,
					config: POP_SPRING,
					durationInFrames: Math.max(1, r.enterDur * fps),
				});
				s.scale *= 0.85 + 0.15 * sp;
				s.opacity *= easeOut(clamp(p / 0.6, 0, 1));
				break;
			}
			case 'slide-up':
				s.dy += SLIDE * (1 - easeOut(p));
				s.opacity *= easeOut(clamp(p / 0.7, 0, 1));
				break;
			case 'slide-left':
				s.dx += SLIDE * (1 - easeOut(p));
				s.opacity *= easeOut(clamp(p / 0.7, 0, 1));
				break;
			case 'slide-right':
				s.dx -= SLIDE * (1 - easeOut(p));
				s.opacity *= easeOut(clamp(p / 0.7, 0, 1));
				break;
			case 'fade':
				s.opacity *= easeInOut(p);
				break;
			case 'grow':
				// bar tự mọc chiều cao; các loại khác phóng to từ 0
				if (el.type !== 'bar') s.scale *= easeOut(p);
				s.opacity *= clamp(p * 3, 0, 1);
				break;
			case 'draw':
				// trace map: tuyến tính để tốc độ bút đều
				s.draw = el.type === 'image' && el.trace && geom.trace ? p : easeDraw(p);
				break;
			case 'none':
				break;
		}
	}

	// --- grayscale (ảnh "phủ bụi") ---
	if (el.type === 'image' && el.grayscale) {
		const g = el.grayscale;
		s.grayscale = clamp(g.to, 0, 1) * easeInOut(progress(t, g.at, g.duration ?? 0.8));
	}

	// --- exit ---
	if (r.exitAt !== null && t >= r.exitAt) {
		const q = progress(t, r.exitAt, r.exitDur);
		if (r.exit === 'none' || q >= 1) {
			s.visible = false;
			return s;
		}
		switch (r.exit) {
			case 'fade':
				s.opacity *= 1 - easeInOut(q);
				break;
			case 'slide-down':
				s.dy += SLIDE * easeIn(q);
				s.opacity *= 1 - easeIn(q);
				break;
			case 'shrink':
				s.scale *= 1 - 0.4 * easeIn(q);
				s.opacity *= 1 - easeIn(q);
				break;
		}
	}
	// --- idle: rung rung liên tục khi đang hiện (nhân vật hoạt hình, plan/16) ---
	if (el.idle?.type === 'rung' && s.visible && s.opacity > 0.001) {
		const amp = el.idle.amplitude ?? 2.5;
		const hz = el.idle.speed ?? 1.6;
		const w = t * hz * Math.PI * 2;
		s.rotate += Math.sin(w) * amp;
		if (el.idle.scaleAmp) s.scale *= 1 + Math.sin(w + Math.PI / 2) * el.idle.scaleAmp;
	}

	if (s.opacity <= 0.001) s.visible = false;
	return s;
};

/** Biến điểm local (so với neo) sang toạ độ scene theo state hiện tại */
export const toScene = (s: ElementState, local: Vec): Vec => {
	const a = (s.rotate * Math.PI) / 180;
	const lx = local.x * s.scale;
	const ly = local.y * s.scale;
	return {
		x: s.x + s.dx + lx * Math.cos(a) - ly * Math.sin(a),
		y: s.y + s.dy + lx * Math.sin(a) + ly * Math.cos(a),
	};
};

export interface HandPose {
	x: number;
	y: number;
	opacity: number;
	active: boolean;
	startedAt: number;
}

const LEAD = 0.3;
const TAIL = 0.4;

/** Vị trí tay vẽ (toạ độ scene) hoặc null nếu không hiện tay */
export const handPose = (r: Resolved, s: ElementState, t: number): HandPose | null => {
	if (!r.hand || r.enter !== 'draw') return null;
	const t0 = r.enterAt;
	const t1 = r.enterAt + r.enterDur;
	if (t < t0 - LEAD || t > t1 + TAIL) return null;
	if (r.exitAt !== null && t >= r.exitAt) return null;
	const p = t < t0 ? 0 : t > t1 ? 1 : (s.draw ?? 1);
	const tip = toScene({...s, visible: true}, r.geom.tipAt(p));
	let k = 0;
	let off = {x: 0, y: 0};
	if (t < t0) {
		k = (t0 - t) / LEAD;
		const e = easeIn(k);
		off = {x: 160 * e, y: 220 * e};
	} else if (t > t1) {
		k = (t - t1) / TAIL;
		const e = easeIn(k);
		off = {x: 220 * e, y: 260 * e};
	}
	// tay giữ đậm khi rút ra, chỉ mờ ở đoạn cuối
	const op = t < t0 ? 1 - Math.pow(clamp(k, 0, 1), 2) : 1 - Math.pow(clamp(k, 0, 1), 3);
	return {x: tip.x + off.x, y: tip.y + off.y, opacity: op, active: t >= t0 && t <= t1, startedAt: t0};
};

/**
 * Chỉ giữ MỘT bàn tay: ưu tiên element đang vẽ bắt đầu muộn nhất;
 * nếu không có element nào đang vẽ thì lấy pose vào/ra gần nhất.
 */
export const pickHand = (poses: HandPose[]): HandPose | null => {
	if (poses.length === 0) return null;
	const active = poses.filter((p) => p.active);
	const pool = active.length ? active : poses;
	return pool.reduce((a, b) => (b.startedAt > a.startedAt ? b : a));
};
