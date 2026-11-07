import type {Vec} from '../types';

export interface PathInfo {
	length: number;
	bbox: {x: number; y: number; w: number; h: number};
	pointAt: (l: number) => Vec;
}

const cache = new Map<string, PathInfo>();
let svgRoot: SVGSVGElement | null = null;

/** Đo path SVG bằng DOM ẩn (chạy trong trình duyệt khi render). Có cache. */
export const getPathInfo = (d: string): PathInfo => {
	const hit = cache.get(d);
	if (hit) return hit;
	if (typeof document === 'undefined') {
		return {length: 0, bbox: {x: 0, y: 0, w: 0, h: 0}, pointAt: () => ({x: 0, y: 0})};
	}
	if (!svgRoot) {
		svgRoot = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		svgRoot.setAttribute('width', '0');
		svgRoot.setAttribute('height', '0');
		svgRoot.style.position = 'absolute';
		svgRoot.style.visibility = 'hidden';
		svgRoot.style.pointerEvents = 'none';
		document.body.appendChild(svgRoot);
	}
	const el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
	el.setAttribute('d', d);
	svgRoot.appendChild(el);
	const length = el.getTotalLength();
	const b = el.getBBox();
	// Lấy mẫu sẵn để các frame sau không phải gọi DOM
	const N = Math.max(32, Math.min(2000, Math.ceil(length / 4)));
	const samples: Vec[] = [];
	for (let i = 0; i <= N; i++) {
		const p = el.getPointAtLength((length * i) / N);
		samples.push({x: p.x, y: p.y});
	}
	svgRoot.removeChild(el);
	const info: PathInfo = {
		length,
		bbox: {x: b.x, y: b.y, w: b.width, h: b.height},
		pointAt: (l: number) => {
			if (length <= 0) return samples[0];
			const f = (Math.min(length, Math.max(0, l)) / length) * N;
			const i = Math.floor(f);
			const a = samples[i];
			const c = samples[Math.min(N, i + 1)];
			const k = f - i;
			return {x: a.x + (c.x - a.x) * k, y: a.y + (c.y - a.y) * k};
		},
	};
	cache.set(d, info);
	return info;
};
