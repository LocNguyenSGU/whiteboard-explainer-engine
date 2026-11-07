import type {CameraKey} from '../types';
import {easeInOut, lerp, progress} from './math';

export interface Cam {
	x: number;
	y: number;
	scale: number;
}

export const DEFAULT_CAM: Cam = {x: 960, y: 540, scale: 1};

/** Nội suy keyframe camera (easeInOut giữa 2 key, giữ nguyên ngoài khoảng) */
export const cameraAt = (
	keys: CameraKey[] | undefined,
	t: number,
	fallback: Cam = DEFAULT_CAM,
): Cam => {
	if (!keys || keys.length === 0) return fallback;
	const ks = [...keys].sort((a, b) => a.at - b.at);
	const toCam = (k: CameraKey): Cam => ({x: k.x, y: k.y, scale: k.scale ?? 1});
	if (t <= ks[0].at) return toCam(ks[0]);
	const last = ks[ks.length - 1];
	if (t >= last.at) return toCam(last);
	for (let i = 0; i < ks.length - 1; i++) {
		const a = ks[i];
		const b = ks[i + 1];
		if (t >= a.at && t <= b.at) {
			const p = easeInOut(progress(t, a.at, b.at - a.at));
			return {
				x: lerp(a.x, b.x, p),
				y: lerp(a.y, b.y, p),
				scale: lerp(a.scale ?? 1, b.scale ?? 1, p),
			};
		}
	}
	return toCam(last);
};

export const lerpCam = (a: Cam, b: Cam, p: number): Cam => ({
	x: lerp(a.x, b.x, p),
	y: lerp(a.y, b.y, p),
	// nội suy scale theo log để zoom cảm giác đều
	scale: Math.exp(lerp(Math.log(a.scale), Math.log(b.scale), p)),
});

/** transform CSS: điểm (x,y) của không gian nội dung nằm giữa khung hình */
export const camTransform = (cam: Cam, w = 1920, h = 1080) =>
	`translate(${w / 2}px, ${h / 2}px) scale(${cam.scale}) translate(${-cam.x}px, ${-cam.y}px)`;
