import type {Vec} from '../types';
import {makePolyline, type Polyline, seededRandom} from './math';

export interface Scribble {
	poly: Polyline;
	d: string;
	strokeWidth: number;
	/** độ dài ~1 nhịp zig-zag, dùng để làm mượt vị trí tay */
	zig: number;
}

const cache = new Map<string, Scribble>();

/**
 * Sinh nét "tô nguệch ngoạc" zig-zag quét bounding box theo từng hàng
 * (boustrophedon). Nét dày strokeWidth phủ kín vùng ảnh khi đi hết.
 * Toạ độ local: (0,0) là góc trên-trái của ảnh.
 */
export const getScribble = (w: number, h: number, seed: string): Scribble => {
	const key = `${seed}|${Math.round(w)}|${Math.round(h)}`;
	const hit = cache.get(key);
	if (hit) return hit;

	const rand = seededRandom(key);
	const target = Math.min(70, Math.max(26, Math.min(w, h) / 5));
	const rows = Math.max(2, Math.ceil(h / target));
	const rowH = h / rows;
	const step = rowH * 0.5;
	const over = rowH * 0.35;
	const padX = rowH * 0.3;
	const pts: Vec[] = [];
	for (let r = 0; r < rows; r++) {
		const yTop = r * rowH - over;
		const yBot = (r + 1) * rowH + over;
		const n = Math.ceil((w + 2 * padX) / step);
		const ltr = r % 2 === 0;
		for (let i = 0; i <= n; i++) {
			const k = ltr ? i : n - i;
			const x = -padX + k * step + (rand() - 0.5) * step * 0.35;
			const top = (i + r) % 2 === 0;
			const y = (top ? yTop : yBot) + (rand() - 0.5) * rowH * 0.18;
			pts.push({x, y});
		}
	}
	const poly = makePolyline(pts);
	const d = pts
		.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
		.join(' ');
	const s: Scribble = {
		poly,
		d,
		strokeWidth: rowH * 1.05,
		zig: Math.hypot(step, rowH + 2 * over),
	};
	cache.set(key, s);
	return s;
};
