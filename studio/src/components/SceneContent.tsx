import React, {useMemo} from 'react';
import {Img} from 'remotion';
import {computeState, handPose, pickHand, type ElementState, type HandPose} from '../lib/anim';
import {resolveAsset} from '../lib/assets';
import {resolveElement, type Ctx, type Resolved} from '../lib/resolve';
import type {HandConfig, Scene} from '../types';
import {
	BarView,
	CaptionView,
	CardView,
	ClockView,
	CounterView,
	ImageView,
	PathView,
	ShapeView,
	TextView,
} from './elements';

export const useResolvedScene = (scene: Scene, ctx: Ctx, fontsOk: boolean): Resolved[] =>
	// eslint-disable-next-line react-hooks/exhaustive-deps
	useMemo(() => scene.elements.map((el) => resolveElement(el, scene, ctx)), [scene, ctx, fontsOk]);

const ElementBody: React.FC<{r: Resolved; s: ElementState; ctx: Ctx; t: number}> = ({r, s, ctx, t}) => {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const props = {r, s, ctx, t} as any;
	switch (r.el.type) {
		case 'image':
			return <ImageView {...props} />;
		case 'text':
			return <TextView {...props} />;
		case 'counter':
			return <CounterView {...props} />;
		case 'card':
			return <CardView {...props} />;
		case 'bar':
			return <BarView {...props} />;
		case 'path':
			return <PathView {...props} />;
		case 'rect':
		case 'circle':
			return <ShapeView {...props} />;
		case 'clock':
			return <ClockView {...props} />;
		case 'caption':
			return <CaptionView {...props} />;
		default:
			return null;
	}
};

/**
 * Nội dung 1 scene trong hệ toạ độ 1920x1080 của scene.
 * layer='elements' vẽ các element; layer='hands' chỉ vẽ tay (đặt trên cùng).
 */
export const SceneContent: React.FC<{
	resolved: Resolved[];
	ctx: Ctx;
	t: number;
	layer: 'elements' | 'hands';
	hand?: HandConfig | null;
	handUrl?: string;
}> = ({resolved, ctx, t, layer, hand}) => {
	const items = resolved
		.map((r, i) => ({r, i, s: computeState(r, t, ctx.fps)}))
		.sort((a, b) => (a.r.el.z ?? 0) - (b.r.el.z ?? 0) || a.i - b.i);

	if (layer === 'hands') {
		if (!hand) return null;
		const url = resolveAsset(ctx.videoId, hand.src);
		const nat = ctx.imageSizes[url] ?? {w: 400, h: 400};
		const scale = hand.scale ?? 1;
		const poses = items.map(({r, s}) => handPose(r, s, t)).filter((p): p is HandPose => p !== null);
		const pose = pickHand(poses);
		if (!pose || pose.opacity <= 0.001) return null;
		return (
			<Img
				src={url}
				style={{
					position: 'absolute',
					left: pose.x - hand.tip.x * scale,
					top: pose.y - hand.tip.y * scale,
					width: nat.w * scale,
					height: nat.h * scale,
					opacity: pose.opacity,
					pointerEvents: 'none',
				}}
			/>
		);
	}

	return (
		<>
			{items.map(({r, s}) => {
				if (!s.visible) return null;
				const tf = [
					`translate(${s.dx.toFixed(2)}px, ${s.dy.toFixed(2)}px)`,
					s.rotate ? `rotate(${s.rotate}deg)` : '',
					s.scale !== 1 ? `scale(${s.scale.toFixed(4)})` : '',
					s.rotateY ? `perspective(1400px) rotateY(${s.rotateY.toFixed(2)}deg)` : '',
				].join(' ');
				return (
					<div
						key={r.el.id}
						data-el={r.el.id}
						style={{
							position: 'absolute',
							left: s.x,
							top: s.y,
							width: 0,
							height: 0,
							transform: tf,
							transformOrigin: '0 0',
							opacity: s.opacity,
						}}
					>
						<ElementBody r={r} s={s} ctx={ctx} t={t} />
					</div>
				);
			})}
		</>
	);
};
