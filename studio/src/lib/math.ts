import {Easing} from 'remotion';
import type {Vec} from '../types';

export const clamp = (v: number, lo: number, hi: number) =>
	Math.min(hi, Math.max(lo, v));

export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;

/** Tiến độ tuyến tính 0..1 của t trong [start, start+dur] */
export const progress = (t: number, start: number, dur: number) =>
	dur <= 0 ? (t >= start ? 1 : 0) : clamp((t - start) / dur, 0, 1);

export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const easeOut = Easing.bezier(0.22, 1, 0.36, 1);
export const easeIn = Easing.bezier(0.55, 0, 1, 0.45);
/** ease nhẹ cho nét vẽ: gần tuyến tính, mềm ở hai đầu */
export const easeDraw = Easing.bezier(0.33, 0.05, 0.67, 0.95);

/** PRNG xác định (mulberry32) — render phải ổn định giữa các frame */
export const seededRandom = (seedStr: string) => {
	let h = 1779033703 ^ seedStr.length;
	for (let i = 0; i < seedStr.length; i++) {
		h = Math.imul(h ^ seedStr.charCodeAt(i), 3432918353);
		h = (h << 13) | (h >>> 19);
	}
	let a = h >>> 0;
	return () => {
		a |= 0;
		a = (a + 0x6d2b79f5) | 0;
		let t = Math.imul(a ^ (a >>> 15), 1 | a);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
};

/** Polyline với độ dài tích luỹ — dùng cho nét scribble và tay vẽ */
export interface Polyline {
	pts: Vec[];
	cum: number[];
	length: number;
}

export const makePolyline = (pts: Vec[]): Polyline => {
	const cum = [0];
	for (let i = 1; i < pts.length; i++) {
		cum.push(
			cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y),
		);
	}
	return {pts, cum, length: cum[cum.length - 1] ?? 0};
};

export const pointAtLength = (poly: Polyline, l: number): Vec => {
	const {pts, cum} = poly;
	if (pts.length === 0) return {x: 0, y: 0};
	if (l <= 0) return pts[0];
	if (l >= poly.length) return pts[pts.length - 1];
	let lo = 0;
	let hi = cum.length - 1;
	while (hi - lo > 1) {
		const mid = (lo + hi) >> 1;
		if (cum[mid] <= l) lo = mid;
		else hi = mid;
	}
	const seg = cum[hi] - cum[lo] || 1;
	const p = (l - cum[lo]) / seg;
	return {
		x: lerp(pts[lo].x, pts[hi].x, p),
		y: lerp(pts[lo].y, pts[hi].y, p),
	};
};

export const polylineToD = (pts: Vec[]) =>
	pts
		.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
		.join(' ');
