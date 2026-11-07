// Trace map: <asset>.trace.png (grayscale, v/254 = thời điểm pixel được vẽ, 255 = không vẽ)
// + <asset>.trace.json (đường đi đầu bút). Giải mã 1 lần / asset, cache ở module.
import type {TraceData, Vec} from '../types';

export const traceUrls = (src: string) => {
	const base = src.replace(/\.png$/i, '');
	return {png: `${base}.trace.png`, json: `${base}.trace.json`};
};

// ---------------------------------------------------------------- rung tay
// Ý tưởng rung tay chuyển từ geeklee/whiteboard-mask-animation (MIT), render_mask_whiteboard.py
// (_wobble/tip_position): hai sóng sin chồng nhau lệch VUÔNG GÓC với hướng nét, nhân bao
// sin(π·u) để bằng 0 ở đầu/cuối mỗi nét; pha cố định theo chỉ số nét → render lặp lại y hệt.

/** Biên độ rung tay tối đa (px scene 1920x1080). Đặt 0 để tắt hẳn. */
export const HAND_JITTER_PX = 2.5;
/** Bước sóng của sóng chính (px scene); sóng phụ ngắn hơn 2.43 lần (như 3 vs 7.3 chu kỳ ở bản gốc) */
const JITTER_WAVELENGTH_PX = 60;
const JITTER_SECOND_RATIO = 7.3 / 3;
/** Trọng số 2 sóng (1.8 và 0.7 ở bản gốc), chuẩn hoá tổng = 1 để biên độ max ≈ HAND_JITTER_PX */
const JITTER_W1 = 1.8 / 2.5;
const JITTER_W2 = 0.7 / 2.5;

export interface TraceJitter {
	/** biên độ (px scene); 0 = tắt */
	amp: number;
	/** px scene trên 1 px ảnh trace (để amp/bước sóng tính theo px scene) */
	pxScale?: number;
	/** độ lệch pha thêm (vd. băm từ id element) */
	seed?: number;
}

interface TraceStrokes {
	/** độ dài cung tích luỹ tại mỗi điểm (px ảnh) */
	cum: Float64Array;
	/** mỗi đoạn i (điểm i→i+1) thuộc nét nào */
	segStroke: Int32Array;
	/** [điểm đầu, điểm cuối] của từng nét */
	strokes: [number, number][];
}

const strokeCache = new WeakMap<TraceData, TraceStrokes>();

/**
 * trace.json không lưu ranh giới nét, nên tách nét theo khoảng nhảy: một đoạn dài hơn
 * max(3×trung vị, 24px) là lúc nhấc bút / quét tô một hàng → đứng riêng thành một "nét";
 * cũng cắt nét khi chuyển từ pha viền (t < outlineEnd) sang pha tô màu.
 */
const traceStrokes = (tr: TraceData): TraceStrokes => {
	const hit = strokeCache.get(tr);
	if (hit) return hit;
	const path = tr.path;
	const n = path.length;
	const cum = new Float64Array(n);
	const seg: number[] = [];
	for (let i = 1; i < n; i++) {
		const d = Math.hypot(path[i][1] - path[i - 1][1], path[i][2] - path[i - 1][2]);
		seg.push(d);
		cum[i] = cum[i - 1] + d;
	}
	const nz = seg.filter((d) => d > 0).sort((a, b) => a - b);
	const median = nz.length ? nz[nz.length >> 1] : 0;
	const thr = Math.max(3 * median, 24);
	const oe = tr.outlineEnd;
	const phase = (i: number) => (oe !== undefined && path[i][0] >= oe ? 1 : 0);
	const strokes: [number, number][] = [];
	const segStroke = new Int32Array(Math.max(0, n - 1));
	let start = 0;
	for (let i = 0; i < n - 1; i++) {
		if (seg[i] > thr || phase(i) !== phase(i + 1)) {
			if (i > start) strokes.push([start, i]);
			strokes.push([i, i + 1]);
			start = i + 1;
		}
	}
	if (start < n - 1) strokes.push([start, n - 1]);
	strokes.forEach(([a, b], k) => {
		for (let i = a; i < b; i++) segStroke[i] = k;
	});
	const res = {cum, segStroke, strokes};
	strokeCache.set(tr, res);
	return res;
};

/** Tiếp tuyến đơn vị tại điểm j, chỉ xét điểm kề trong cùng nét [a,b] */
const tangentAt = (path: TraceData['path'], j: number, a: number, b: number): Vec => {
	const p0 = path[Math.max(a, j - 1)];
	const p1 = path[Math.min(b, j + 1)];
	const dx = p1[1] - p0[1];
	const dy = p1[2] - p0[2];
	const l = Math.hypot(dx, dy);
	return l > 0 ? {x: dx / l, y: dy / l} : {x: 0, y: 0};
};

/**
 * Vị trí đầu bút (pixel ảnh) tại tiến độ p, nội suy tuyến tính giữa 2 điểm kề,
 * cộng rung tay (nếu `jitter.amp` > 0) lệch vuông góc với hướng nét, = 0 ở hai đầu mỗi nét.
 * Hàm thuần: cùng (tr, p, jitter) → cùng kết quả. Chỉ dùng cho vị trí tay; mực lộ ra theo
 * trace.png nên biên độ phải nhỏ để tay không lệch khỏi nét mực.
 */
export const tracePointAt = (tr: TraceData, p: number, jitter?: TraceJitter): Vec => {
	const path = tr.path;
	if (!path.length) return {x: tr.width / 2, y: tr.height / 2};
	if (p <= path[0][0]) return {x: path[0][1], y: path[0][2]};
	const last = path[path.length - 1];
	if (p >= last[0]) return {x: last[1], y: last[2]};
	let lo = 0;
	let hi = path.length - 1;
	while (hi - lo > 1) {
		const mid = (lo + hi) >> 1;
		if (path[mid][0] <= p) lo = mid;
		else hi = mid;
	}
	const a = path[lo];
	const b = path[hi];
	const k = b[0] > a[0] ? (p - a[0]) / (b[0] - a[0]) : 1;
	const x = a[1] + (b[1] - a[1]) * k;
	const y = a[2] + (b[2] - a[2]) * k;
	if (!jitter || !(jitter.amp > 0)) return {x, y};

	const {cum, segStroke, strokes} = traceStrokes(tr);
	const si = segStroke[lo];
	const [s0, s1] = strokes[si];
	const L = cum[s1] - cum[s0];
	if (!(L > 0)) return {x, y};
	const sLocal = cum[lo] + (cum[hi] - cum[lo]) * k - cum[s0];
	const u = sLocal / L;
	const scale = jitter.pxScale && jitter.pxScale > 0 ? jitter.pxScale : 1;
	const seed = si * 2.399963 + (jitter.seed ?? 0); // góc vàng → các nét lệch pha nhau
	const cyc = (sLocal * scale) / JITTER_WAVELENGTH_PX;
	const w =
		Math.sin(Math.PI * u) *
		(JITTER_W1 * Math.sin(2 * Math.PI * cyc + seed) +
			JITTER_W2 * Math.sin(2 * Math.PI * cyc * JITTER_SECOND_RATIO + seed * 1.7));
	// pháp tuyến nội suy giữa 2 đỉnh → offset liên tục khi qua đỉnh gấp khúc
	const ta = tangentAt(path, lo, s0, s1);
	const tb = tangentAt(path, hi, s0, s1);
	let tx = ta.x + (tb.x - ta.x) * k;
	let ty = ta.y + (tb.y - ta.y) * k;
	const tl = Math.hypot(tx, ty);
	if (!(tl > 0)) return {x, y};
	tx /= tl;
	ty /= tl;
	const off = (w * jitter.amp) / scale; // px scene → px ảnh
	return {x: x - ty * off, y: y + tx * off};
};

export interface TracePixels {
	width: number;
	height: number;
	/** RGBA của ảnh gốc */
	rgba: Uint8ClampedArray;
	/** giá trị trace (0..255) mỗi pixel */
	order: Uint8Array;
	/** bộ đệm tái sử dụng cho mỗi frame */
	out: ImageData;
}

const cache = new Map<string, TracePixels>();
const pending = new Map<string, Promise<TracePixels>>();

const loadImage = (url: string) =>
	new Promise<HTMLImageElement>((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = () => reject(new Error(`Không tải được ${url}`));
		img.src = url;
	});

const pixelsOf = (img: HTMLImageElement, w: number, h: number) => {
	const c = document.createElement('canvas');
	c.width = w;
	c.height = h;
	const g = c.getContext('2d', {willReadFrequently: true});
	if (!g) throw new Error('canvas 2d không khả dụng');
	g.drawImage(img, 0, 0, w, h);
	return g.getImageData(0, 0, w, h).data;
};

export const getTracePixelsSync = (imgUrl: string) => cache.get(imgUrl) ?? null;

/** Giải mã ảnh gốc + trace.png thành mảng pixel (chạy 1 lần cho mỗi asset) */
export const loadTracePixels = (imgUrl: string, traceUrl: string): Promise<TracePixels> => {
	const hit = cache.get(imgUrl);
	if (hit) return Promise.resolve(hit);
	let pr = pending.get(imgUrl);
	if (!pr) {
		pr = Promise.all([loadImage(imgUrl), loadImage(traceUrl)]).then(([img, tr]) => {
			const width = img.naturalWidth;
			const height = img.naturalHeight;
			const rgba = pixelsOf(img, width, height);
			// trace map co giãn về đúng kích thước ảnh nếu lệch (nearest neighbour)
			const tw = tr.naturalWidth;
			const th = tr.naturalHeight;
			const trData = pixelsOf(tr, tw, th);
			const order = new Uint8Array(width * height);
			for (let y = 0; y < height; y++) {
				const ty = Math.min(th - 1, Math.floor((y * th) / height));
				for (let x = 0; x < width; x++) {
					const tx = Math.min(tw - 1, Math.floor((x * tw) / width));
					order[y * width + x] = trData[(ty * tw + tx) * 4];
				}
			}
			const tp: TracePixels = {width, height, rgba, order, out: new ImageData(width, height)};
			cache.set(imgUrl, tp);
			pending.delete(imgUrl);
			return tp;
		});
		pending.set(imgUrl, pr);
	}
	return pr;
};

/** Ghi vào tp.out: chỉ giữ pixel có trace ≤ p*254 */
export const composeTrace = (tp: TracePixels, p: number): ImageData => {
	const thr = Math.floor(Math.max(0, Math.min(1, p)) * 254);
	const {rgba, order} = tp;
	const out = tp.out.data;
	const n = order.length;
	for (let i = 0; i < n; i++) {
		const j = i * 4;
		if (order[i] <= thr) {
			out[j] = rgba[j];
			out[j + 1] = rgba[j + 1];
			out[j + 2] = rgba[j + 2];
			out[j + 3] = rgba[j + 3];
		} else {
			out[j + 3] = 0;
		}
	}
	return tp.out;
};
