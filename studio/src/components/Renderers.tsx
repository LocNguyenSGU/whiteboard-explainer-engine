import React, {useMemo} from 'react';
import {AbsoluteFill, Img} from 'remotion';
import {computeState, toScene} from '../lib/anim';
import {camTransform, cameraAt, DEFAULT_CAM, lerpCam, type Cam} from '../lib/camera';
import {clamp, easeInOut, easeOut, progress, seededRandom} from '../lib/math';
import {resolveElement, type Ctx} from '../lib/resolve';
import type {Scene, Timeline, TransitionType, Vec} from '../types';
import {SceneContent, useResolvedScene} from './SceneContent';

export interface NormTransition {
	type: TransitionType;
	d: number;
	fromElement?: string;
	dip: number;
}

/** Chuẩn hoá transitionIn theo style (mặc định A/B: fade 0.3s; C: pan 1.0s) */
export const normTransition = (scene: Scene, index: number, style: Timeline['style']): NormTransition => {
	if (index === 0) return {type: 'none', d: 0, dip: 0};
	const ti = scene.transitionIn;
	const isC = style === 'C';
	const type: TransitionType = ti?.type ?? (isC ? 'pan' : 'fade');
	const defDur = type === 'pan' ? 1.0 : type === 'zoom-from' ? 0.7 : 0.35;
	const d = type === 'none' ? 0 : Math.max(0, ti?.duration ?? defDur);
	return {type, d, fromElement: ti?.fromElement, dip: clamp(ti?.dip ?? 0.12, 0, 0.5)};
};

export const sortedScenes = (tl: Timeline) => [...tl.scenes].sort((a, b) => a.start - b.start);

// ======================================================= Style A / B: chồng scene + transition
const SceneLayer: React.FC<{
	scene: Scene;
	tl: Timeline;
	ctx: Ctx;
	t: number;
	fontsOk: boolean;
	wrapper: React.CSSProperties;
	cam: Cam;
}> = ({scene, tl, ctx, t, fontsOk, wrapper, cam}) => {
	const resolved = useResolvedScene(scene, ctx, fontsOk);
	return (
		<AbsoluteFill style={{background: scene.background ?? tl.background ?? '#F7F8FA', overflow: 'hidden', ...wrapper}}>
			<div
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					width: tl.width,
					height: tl.height,
					transformOrigin: '0 0',
					transform: camTransform(cam, tl.width, tl.height),
				}}
			>
				<SceneContent resolved={resolved} ctx={ctx} t={t} layer="elements" />
				<SceneContent resolved={resolved} ctx={ctx} t={t} layer="hands" hand={tl.hand} />
			</div>
		</AbsoluteFill>
	);
};

/** Bounding box (toạ độ scene) của element dùng cho zoom-from */
const elementBounds = (scene: Scene, id: string | undefined, ctx: Ctx, t: number) => {
	const el = scene.elements.find((e) => e.id === id);
	if (!el) return null;
	const r = resolveElement(el, scene, ctx);
	const s = computeState(r, t, ctx.fps);
	const b = r.geom.box;
	const c = toScene(s, {x: b.ox + b.w / 2, y: b.oy + b.h / 2});
	return {x: c.x, y: c.y, w: b.w * s.scale, h: b.h * s.scale};
};

export const SceneStack: React.FC<{tl: Timeline; ctx: Ctx; t: number; fontsOk: boolean}> = ({tl, ctx, t, fontsOk}) => {
	const scenes = sortedScenes(tl);
	const W = tl.width;
	const H = tl.height;
	const trs = scenes.map((s, i) => normTransition(s, i, tl.style));
	const layers: React.ReactNode[] = [];
	scenes.forEach((scene, i) => {
		const visStart = i === 0 ? -Infinity : scene.start - trs[i].d;
		const visEnd = i < scenes.length - 1 ? scenes[i + 1].start : Infinity;
		if (t < visStart || t >= visEnd) return;
		const wrapper: React.CSSProperties = {};
		const transforms: string[] = [];
		let cam = cameraAt(scene.camera, t, DEFAULT_CAM);

		// ---- scene đang vào
		const tin = trs[i];
		if (tin.d > 0 && t < scene.start) {
			const p = progress(t, visStart, tin.d);
			switch (tin.type) {
				case 'fade':
					wrapper.opacity = easeInOut(p);
					break;
				case 'push-left':
				case 'pan':
					transforms.push(`translateX(${((1 - easeInOut(p)) * W).toFixed(2)}px)`);
					break;
				case 'push-up':
					transforms.push(`translateY(${((1 - easeInOut(p)) * H).toFixed(2)}px)`);
					break;
				case 'zoom-from': {
					const q = clamp((p - 0.45) / 0.55, 0, 1);
					wrapper.opacity = easeInOut(q);
					transforms.push(`scale(${(0.94 + 0.06 * easeOut(q)).toFixed(4)})`);
					break;
				}
			}
		}
		// ---- scene đang ra (scene kế tiếp đang transition vào)
		if (i < scenes.length - 1) {
			const next = scenes[i + 1];
			const tn = trs[i + 1];
			if (tn.d > 0 && t >= next.start - tn.d) {
				const q = progress(t, next.start - tn.d, tn.d);
				switch (tn.type) {
					case 'push-left':
					case 'pan':
						transforms.push(`translateX(${(-easeInOut(q) * W).toFixed(2)}px)`);
						break;
					case 'push-up':
						transforms.push(`translateY(${(-easeInOut(q) * H).toFixed(2)}px)`);
						break;
					case 'zoom-from': {
						const b = elementBounds(scene, tn.fromElement, ctx, t);
						if (b) {
							const target: Cam = {
								x: b.x,
								y: b.y,
								scale: clamp(Math.min(W / Math.max(b.w, 1), H / Math.max(b.h, 1)) * 0.75, 1.2, 8),
							};
							cam = lerpCam(cam, target, Math.pow(clamp(q / 0.85, 0, 1), 2));
						} else {
							cam = lerpCam(cam, {...cam, scale: cam.scale * 2.5}, Math.pow(q, 2));
						}
						break;
					}
				}
			}
		}
		if (transforms.length) {
			wrapper.transform = transforms.join(' ');
			wrapper.transformOrigin = '50% 50%';
		}
		layers.push(
			<SceneLayer key={scene.id} scene={scene} tl={tl} ctx={ctx} t={t} fontsOk={fontsOk} wrapper={wrapper} cam={cam} />,
		);
	});
	return <>{layers}</>;
};

// ======================================================= Style C: 1 bảng trắng liên tục
const defaultOrigin = (i: number): Vec => ({x: i * (1920 + 240), y: 0});

const BoardScene: React.FC<{
	scene: Scene;
	origin: Vec;
	tl: Timeline;
	ctx: Ctx;
	t: number;
	fontsOk: boolean;
	layer: 'elements' | 'hands';
}> = ({scene, origin, tl, ctx, t, fontsOk, layer}) => {
	const resolved = useResolvedScene(scene, ctx, fontsOk);
	return (
		<div style={{position: 'absolute', left: origin.x, top: origin.y, width: tl.width, height: tl.height}}>
			<SceneContent resolved={resolved} ctx={ctx} t={t} layer={layer} hand={tl.hand} />
		</div>
	);
};

/** Ảnh nhiễu giấy (xác định, sinh 1 lần bằng canvas) */
const useNoiseTile = (): string | null =>
	useMemo(() => {
		if (typeof document === 'undefined') return null;
		// nhiễu mịn: sinh 128px rồi phóng 2x (nội suy) → hạt mềm, ít tốn bitrate
		const small = 128;
		const src = document.createElement('canvas');
		src.width = small;
		src.height = small;
		const sg = src.getContext('2d');
		if (!sg) return null;
		const img = sg.createImageData(small, small);
		const rand = seededRandom('paper');
		for (let i = 0; i < small * small; i++) {
			const dark = rand() < 0.55;
			const a = Math.pow(rand(), 2) * 22;
			img.data[i * 4] = dark ? 90 : 255;
			img.data[i * 4 + 1] = dark ? 84 : 255;
			img.data[i * 4 + 2] = dark ? 72 : 250;
			img.data[i * 4 + 3] = a;
		}
		sg.putImageData(img, 0, 0);
		const c = document.createElement('canvas');
		c.width = small * 2;
		c.height = small * 2;
		const g = c.getContext('2d');
		if (!g) return null;
		g.imageSmoothingEnabled = true;
		g.imageSmoothingQuality = 'high';
		g.drawImage(src, 0, 0, small * 2, small * 2);
		return c.toDataURL('image/png');
	}, []);

export const boardCamera = (tl: Timeline, t: number): {cam: Cam; origins: Vec[]; scenes: Scene[]} => {
	const scenes = sortedScenes(tl);
	const origins = scenes.map((s, i) => s.origin ?? defaultOrigin(i));
	const sceneCam = (i: number): Cam => {
		const o = origins[i];
		const c = cameraAt(scenes[i].camera, t, DEFAULT_CAM);
		return {x: c.x + o.x, y: c.y + o.y, scale: c.scale};
	};
	// scene hiện tại = scene cuối cùng đã bắt đầu transition
	let k = 0;
	for (let i = 0; i < scenes.length; i++) {
		const tr = normTransition(scenes[i], i, 'C');
		if (t >= scenes[i].start - tr.d) k = i;
	}
	const tr = normTransition(scenes[k], k, 'C');
	let cam = sceneCam(k);
	if (k > 0 && tr.d > 0 && t < scenes[k].start) {
		const p = progress(t, scenes[k].start - tr.d, tr.d);
		const e = easeInOut(p);
		cam = lerpCam(sceneCam(k - 1), cam, e);
		cam.scale *= 1 - tr.dip * Math.sin(Math.PI * p);
	}
	return {cam, origins, scenes};
};

export const Board: React.FC<{tl: Timeline; ctx: Ctx; t: number; fontsOk: boolean}> = ({tl, ctx, t, fontsOk}) => {
	const {cam, origins, scenes} = boardCamera(tl, t);
	const noise = useNoiseTile();
	const W = tl.width;
	const H = tl.height;
	// culling: chỉ render scene có vùng giao với khung nhìn (+lề)
	const halfW = W / 2 / cam.scale + 400;
	const halfH = H / 2 / cam.scale + 400;
	const visible = scenes
		.map((s, i) => ({s, o: origins[i]}))
		.filter(
			({o}) =>
				o.x < cam.x + halfW && o.x + W > cam.x - halfW && o.y < cam.y + halfH && o.y + H > cam.y - halfH,
		);
	const tile = 256 * cam.scale;
	const noiseOn = tl.paperNoise ?? true;
	return (
		<AbsoluteFill style={{background: tl.background ?? '#FCFCFA', overflow: 'hidden'}}>
			{noise && noiseOn ? (
				<>
					<Img src={noise} style={{position: 'absolute', width: 1, height: 1, opacity: 0}} />
					<AbsoluteFill
						style={{
							backgroundImage: `url(${noise})`,
							backgroundSize: tl.noiseStatic ? '256px 256px' : `${tile}px ${tile}px`,
							backgroundPosition: tl.noiseStatic ? '0px 0px' : `${(-cam.x * cam.scale + W / 2).toFixed(2)}px ${(-cam.y * cam.scale + H / 2).toFixed(2)}px`,
						}}
					/>
				</>
			) : null}
			<div
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					width: tl.board?.width ?? W,
					height: tl.board?.height ?? H,
					transformOrigin: '0 0',
					transform: camTransform(cam, W, H),
				}}
			>
				{visible.map(({s, o}) => (
					<BoardScene key={s.id} scene={s} origin={o} tl={tl} ctx={ctx} t={t} fontsOk={fontsOk} layer="elements" />
				))}
				{visible.map(({s, o}) => (
					<BoardScene key={`h-${s.id}`} scene={s} origin={o} tl={tl} ctx={ctx} t={t} fontsOk={fontsOk} layer="hands" />
				))}
			</div>
		</AbsoluteFill>
	);
};
