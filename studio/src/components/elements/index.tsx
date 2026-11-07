import React, {useEffect, useId, useLayoutEffect, useRef, useState} from 'react';
import {cancelRender, continueRender, delayRender, Img, OffthreadVideo, Sequence, useVideoConfig} from 'remotion';
import {composeTrace, getTracePixelsSync, loadTracePixels, traceUrls} from '../../lib/trace';
import {SvgImage} from '../SvgImage';
import {fontFamily} from '../../fonts';
import type {ElementState} from '../../lib/anim';
import {resolveAsset} from '../../lib/assets';
import {formatVi} from '../../lib/format';
import {clamp, easeInOut, easeOut, lerp, polylineToD, progress} from '../../lib/math';
import {counterText, lineLeft, SHAPE_LABEL_PAD, type Ctx, type Resolved} from '../../lib/resolve';
import {revealFractions, type RoughDrawing} from '../../lib/rough';
import type {
	BarElement,
	CaptionElement,
	CardElement,
	ClockElement,
	CounterElement,
	ImageElement,
	PathElement,
	ShapeElement,
	TextElement,
} from '../../types';

export interface ElProps<E> {
	r: Resolved & {el: E};
	s: ElementState;
	ctx: Ctx;
	t: number;
}

const INK = '#1D2433';
const ORANGE = '#F2611D';

const useSafeId = (prefix: string) => `${prefix}${useId().replace(/[^a-zA-Z0-9]/g, '')}`;

/**
 * Bọc nội dung vẽ: dùng "lau" trái→phải khi enter=draw cho các loại không có nét riêng.
 * `bleedY` (px, tuỳ chọn): phần tràn trên/dưới không bị cắt — cho khung rất thấp (bar ngang);
 * bỏ trống = giữ nguyên -40%/-60% theo chiều cao khung.
 */
const Wipe: React.FC<{p: number | null; bleedY?: number; children: React.ReactNode}> = ({p, bleedY, children}) => {
	if (p === null || p >= 1) return <>{children}</>;
	const right = `${((1 - p) * 100).toFixed(3)}%`;
	return (
		<div
			style={{
				position: 'absolute',
				inset: 0,
				clipPath:
					bleedY === undefined
						? `inset(-40% ${right} -60% -10%)`
						: `inset(-${bleedY}px ${right} -${bleedY}px -10%)`,
			}}
		>
			{children}
		</div>
	);
};

// ---------------------------------------------------------------- image
/** Đoạn video thật trong khung ảnh: phát từ lúc element hiện (cảnh không nằm trong Sequence nên mốc là khung tuyệt đối). */
const ClipBody: React.FC<{src: string; at: number; rate: number; w: number; h: number}> = ({src, at, rate, w, h}) => {
	const {fps} = useVideoConfig();
	return (
		<Sequence from={Math.round(at * fps)} layout="none">
			<OffthreadVideo src={src} muted playbackRate={rate} style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
		</Sequence>
	);
};

export const ImageView: React.FC<ElProps<ImageElement>> = ({r, s, ctx}) => {
	const el = r.el;
	const {w, h} = r.geom.imageSize!;
	const url = resolveAsset(ctx.videoId, el.src);
	const maskId = useSafeId('m');
	const tintId = useSafeId('t');
	const drawing = s.draw !== null && s.draw < 1;
	const p = s.draw ?? 1;
	const traced = Boolean(r.geom.trace);
	// cuối nét vẽ: hiện dần ảnh gốc để chắc chắn không còn lỗ hổng
	const solid = drawing ? (traced ? clamp((p - 0.97) / 0.03, 0, 1) : clamp((p - 0.86) / 0.14, 0, 1)) : 1;
	const tint = el.tint ? (typeof el.tint === 'string' ? {color: el.tint, amount: 1} : el.tint) : null;
	const filters: string[] = [];
	if (tint) filters.push(`url(#${tintId})`);
	if (s.grayscale > 0) filters.push(`grayscale(${s.grayscale.toFixed(3)})`);
	if (s.grayscale > 0) filters.push(`brightness(${(1 + 0.08 * s.grayscale).toFixed(3)}) contrast(${(1 - 0.15 * s.grayscale).toFixed(3)})`);
	const sc = r.geom.scribble!;
	const L = sc.poly.length;
	const pad = sc.strokeWidth * 2;
	const flip = el.flipX ? 'scaleX(-1)' : undefined;
	return (
		<div
			style={{
				position: 'absolute',
				left: r.geom.box.ox,
				top: r.geom.box.oy,
				width: w,
				height: h,
				filter: filters.length ? filters.join(' ') : undefined,
			}}
		>
			{tint ? (
				<svg width={0} height={0} style={{position: 'absolute'}}>
					<defs>
						<filter id={tintId} colorInterpolationFilters="sRGB">
							<feFlood floodColor={tint.color} result="f" />
							<feBlend in="SourceGraphic" in2="f" mode="multiply" result="b" />
							<feComposite
								in="b"
								in2="SourceGraphic"
								operator="arithmetic"
								k1={0}
								k2={tint.amount ?? 1}
								k3={1 - (tint.amount ?? 1)}
								k4={0}
								result="m"
							/>
							<feComposite in="m" in2="SourceAlpha" operator="in" />
						</filter>
					</defs>
				</svg>
			) : null}
			{el.video ? (
				<ClipBody src={resolveAsset(ctx.videoId, el.video)} at={el.enterAt ?? 0} rate={el.videoRate ?? 1} w={w} h={h} />
			) : (
				<Img
					src={url}
					style={{position: 'absolute', left: 0, top: 0, width: w, height: h, opacity: solid, transform: flip}}
				/>
			)}
			{drawing && traced ? (
				<TraceCanvas
					imgUrl={url}
					traceUrl={resolveAsset(ctx.videoId, traceUrls(el.src).png)}
					p={p}
					w={w}
					h={h}
					flip={flip}
				/>
			) : null}
			{drawing && !traced ? (
				<svg
					width={w}
					height={h}
					style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', transform: flip}}
				>
					<defs>
						<mask id={maskId} maskUnits="userSpaceOnUse" x={-pad} y={-pad} width={w + pad * 2} height={h + pad * 2}>
							<path
								d={sc.d}
								fill="none"
								stroke="#fff"
								strokeWidth={sc.strokeWidth}
								strokeLinecap="round"
								strokeLinejoin="round"
								strokeDasharray={`${L} ${L}`}
								strokeDashoffset={L * (1 - p)}
							/>
						</mask>
					</defs>
					<SvgImageLazy href={url} w={w} h={h} mask={`url(#${maskId})`} />
				</svg>
			) : null}
		</div>
	);
};

/** Vẽ ảnh theo trace map: chỉ hiện pixel có thứ tự ≤ p (canvas + ImageData, xác định) */
const TraceCanvas: React.FC<{imgUrl: string; traceUrl: string; p: number; w: number; h: number; flip?: string}> = ({
	imgUrl,
	traceUrl,
	p,
	w,
	h,
	flip,
}) => {
	const ref = useRef<HTMLCanvasElement>(null);
	const [tp, setTp] = useState(() => getTracePixelsSync(imgUrl));
	const [handle] = useState(() => (tp ? null : delayRender(`trace ${imgUrl}`, {timeoutInMilliseconds: 60000})));
	const done = useRef(false);
	const release = () => {
		if (handle !== null && !done.current) {
			done.current = true;
			continueRender(handle);
		}
	};
	useEffect(() => {
		if (tp) return;
		let alive = true;
		loadTracePixels(imgUrl, traceUrl)
			.then((d) => alive && setTp(d))
			.catch((e) => cancelRender(e));
		return () => {
			alive = false;
		};
	}, [imgUrl, traceUrl, tp]);
	useEffect(() => release, []); // eslint-disable-line react-hooks/exhaustive-deps
	useLayoutEffect(() => {
		const c = ref.current;
		if (!tp || !c) return;
		const g = c.getContext('2d');
		if (!g) return;
		g.putImageData(composeTrace(tp, p), 0, 0);
		release();
	}); // eslint-disable-line react-hooks/exhaustive-deps
	return (
		<canvas
			ref={ref}
			width={tp?.width ?? 1}
			height={tp?.height ?? 1}
			style={{position: 'absolute', left: 0, top: 0, width: w, height: h, transform: flip}}
		/>
	);
};

const SvgImageLazy: React.FC<{href: string; w: number; h: number; mask: string}> = ({href, w, h, mask}) => (
	<SvgImage href={href} x={0} y={0} width={w} height={h} mask={mask} preserveAspectRatio="none" />
);

// ---------------------------------------------------------------- text
export const TextView: React.FC<ElProps<TextElement>> = ({r, s, ctx}) => {
	const el = r.el;
	const lay = r.geom.text!;
	const box = r.geom.box;
	const size = lay.size;
	const weight = el.weight ?? 600;
	const align = el.align ?? 'center';
	const color = el.color ?? INK;
	const p = s.draw;
	// phân bổ tiến độ vẽ theo độ dài từng dòng
	const total = lay.lines.reduce((a, l) => a + Math.max(l.width, 1), 0);
	let acc = (p ?? 1) * total;
	// T4: khoanh/gạch chân — hiện sau khi chữ vẽ xong (p: 0,6 → 1,0)
	const markDr = el.mark ? r.geom.rough : undefined;
	const markP = p === null ? 1 : clamp((p - 0.6) / 0.4, 0, 1);
	const markId = useSafeId('txm');
	const boxStyle: React.CSSProperties =
		el.box === 'card'
			? {
					background: el.boxColor ?? (ctx.style === 'C' ? 'transparent' : '#FFFFFF'),
					border: ctx.style === 'C' ? `3px solid ${INK}` : '2px solid #E3E6EB',
					borderRadius: 18,
					boxShadow: ctx.style === 'C' ? undefined : '0 6px 20px rgba(29,36,51,0.08)',
				}
			: el.box === 'pill'
				? {background: el.boxColor ?? INK, borderRadius: 9999}
				: {};
	return (
		<>
		<div
			style={{
				position: 'absolute',
				left: box.ox,
				top: box.oy,
				width: box.w,
				height: box.h,
				...boxStyle,
			}}
		>
			{lay.lines.map((line, i) => {
				const lw = Math.max(line.width, 1);
				const f = p === null ? 1 : clamp(acc / lw, 0, 1);
				acc -= lw;
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: lineLeft(lay, i, box.w, lay.pad.x, align),
							top: lay.pad.y + i * lay.lineHeight,
							width: line.width + 2,
							height: lay.lineHeight,
							lineHeight: `${lay.lineHeight}px`,
							whiteSpace: 'pre',
							fontFamily: fontFamily(r.font),
							fontSize: size,
							fontWeight: weight,
							color,
							clipPath: f < 1 ? `inset(-60% ${((1 - f) * 100).toFixed(3)}% -60% -10%)` : undefined,
							visibility: f <= 0 ? 'hidden' : undefined,
						}}
					>
						{line.text}
					</div>
				);
			})}
		</div>
		{markDr && markP > 0 ? (
			<svg width={1} height={1} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
				<g transform={`translate(${box.ox + box.w / 2} ${box.oy + box.h / 2})`}>
					<RoughStrokes dr={markDr} p={markP} stroke={el.markColor ?? ORANGE} sw={el.markWidth ?? 5} maskId={markId} />
				</g>
			</svg>
		) : null}
		</>
	);
};

// ---------------------------------------------------------------- counter
export const CounterView: React.FC<ElProps<CounterElement>> = ({r, s, t}) => {
	const el = r.el;
	const box = r.geom.box;
	const start = el.countAt ?? r.enterAt;
	const v = lerp(el.from, el.to, easeOut(progress(t, start, el.countDuration ?? 1.2)));
	return (
		<div style={{position: 'absolute', left: box.ox, top: box.oy, width: box.w, height: box.h}}>
			<Wipe p={s.draw}>
				<div
					style={{
						width: box.w,
						height: box.h,
						lineHeight: `${box.h}px`,
						textAlign: 'center',
						whiteSpace: 'nowrap',
						fontFamily: fontFamily(r.font),
						fontSize: el.size ?? 96,
						fontWeight: el.weight ?? 800,
						color: el.color ?? INK,
						fontVariantNumeric: 'tabular-nums',
					}}
				>
					{counterText(el, v)}
				</div>
			</Wipe>
		</div>
	);
};

// ---------------------------------------------------------------- card
export const CardView: React.FC<ElProps<CardElement>> = ({r, s, ctx}) => {
	const el = r.el;
	const box = r.geom.box;
	const isC = ctx.style === 'C';
	const fitted = r.geom.cardText;
	// nét tay cho thẻ (T4): viền vẽ bằng rough.js thay viền CSS thẳng khi timeline.rough bật
	const dr = r.geom.rough;
	const sw = isC ? 3 : 2;
	const roughId = useSafeId('rcm');
	return (
		<>
		<div style={{position: 'absolute', left: box.ox, top: box.oy, width: box.w, height: box.h}}>
			<Wipe p={s.draw}>
				<div
					style={{
						position: 'absolute',
						inset: 0,
						background: el.color ?? (isC ? 'transparent' : '#FFFFFF'),
						border: dr ? 'none' : `${sw}px solid ${el.border ?? (isC ? INK : '#E3E6EB')}`,
						borderRadius: el.radius ?? 20,
						boxShadow: isC ? undefined : '0 8px 24px rgba(29,36,51,0.08)',
						overflow: 'hidden',
						display: 'flex',
						flexDirection: 'column',
						alignItems: 'center',
						justifyContent: 'center',
						textAlign: 'center',
						padding: 24,
						boxSizing: 'border-box',
						gap: 12,
						fontFamily: fontFamily(r.font),
					}}
				>
					{el.accent ? (
						<div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 10, background: el.accent}} />
					) : null}
					{el.icon ? (
						<Img
							src={resolveAsset(ctx.videoId, el.icon)}
							style={{maxHeight: box.h * 0.38, maxWidth: box.w * 0.6, objectFit: 'contain'}}
						/>
					) : null}
					{el.title ? (
						fitted?.title ? (
							<div
								style={{
									fontSize: fitted.title.size,
									fontWeight: 800,
									color: el.titleColor ?? INK,
									lineHeight: 1.2,
									whiteSpace: 'pre',
									flexShrink: 0,
								}}
							>
								{fitted.title.lines.join('\n')}
							</div>
						) : (
							<div style={{fontSize: el.titleSize ?? 36, fontWeight: 800, color: el.titleColor ?? INK, lineHeight: 1.2}}>
								{el.title}
							</div>
						)
					) : null}
					{el.body ? (
						fitted?.body ? (
							<div
								style={{
									fontSize: fitted.body.size,
									fontWeight: 400,
									color: el.bodyColor ?? '#4A5263',
									lineHeight: 1.35,
									whiteSpace: 'pre',
									flexShrink: 0,
								}}
							>
								{fitted.body.lines.join('\n')}
							</div>
						) : (
							<div style={{fontSize: el.bodySize ?? 24, fontWeight: 400, color: el.bodyColor ?? '#4A5263', lineHeight: 1.35}}>
								{el.body}
							</div>
						)
					) : null}
				</div>
			</Wipe>
		</div>
		{dr ? (
			<svg width={1} height={1} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
				<RoughStrokes dr={dr} p={s.draw ?? 1} stroke={el.border ?? INK} sw={sw} maskId={roughId} />
			</svg>
		) : null}
		</>
	);
};

// ---------------------------------------------------------------- bar
export const BarView: React.FC<ElProps<BarElement>> = (props) => {
	if (props.r.el.horizontal) return <HBarView {...props} />;
	return <VBarView {...props} />;
};

/** Cột dọc (mặc định): neo đáy-giữa tại (x,y), mọc lên tới value*maxH */
const VBarView: React.FC<ElProps<BarElement>> = ({r, s, t}) => {
	const el = r.el;
	const gp =easeOut(progress(t, el.growAt ?? r.enterAt, el.growDuration ?? 1.0));
	const v = clamp(el.value, 0, 1);
	const h = el.maxH * v * gp;
	const labelSize = clamp(el.w * 0.3, 20, 44);
	return (
		<div style={{position: 'absolute', left: -el.w / 2, top: -el.maxH, width: el.w, height: el.maxH}}>
			<Wipe p={s.draw}>
				{el.track !== null ? (
					<div
						style={{
							position: 'absolute',
							left: 0,
							bottom: 0,
							width: el.w,
							height: el.maxH,
							background: el.track ?? 'rgba(29,36,51,0.06)',
							borderRadius: 12,
						}}
					/>
				) : null}
				<div
					style={{
						position: 'absolute',
						left: 0,
						bottom: 0,
						width: el.w,
						height: h,
						background: el.color ?? '#2F6FEB',
						borderRadius: '12px 12px 4px 4px',
					}}
				/>
				{el.showValue ? (
					<div
						style={{
							position: 'absolute',
							left: -40,
							width: el.w + 80,
							bottom: h + 10,
							textAlign: 'center',
							fontFamily: fontFamily(r.font),
							fontSize: labelSize,
							fontWeight: 800,
							color: el.valueColor ?? el.color ?? '#2F6FEB',
							opacity: clamp(gp * 3, 0, 1),
						}}
					>
						{formatVi(v * 100 * gp, 0)}%
					</div>
				) : null}
				{el.label ? (
					<div
						style={{
							position: 'absolute',
							left: -80,
							width: el.w + 160,
							top: el.maxH + 14,
							textAlign: 'center',
							fontFamily: fontFamily(r.font),
							fontSize: 26,
							fontWeight: 600,
							color: el.labelColor ?? '#4A5263',
						}}
					>
						{el.label}
					</div>
				) : null}
			</Wipe>
		</div>
	);
};

/**
 * Thanh ngang (horizontal: true). Neo: TÂM của rãnh tại (x,y) — rãnh trải [x-w/2, x+w/2] × [y-maxH/2, y+maxH/2].
 * (Cột dọc neo đáy-giữa vì nó mọc lên từ đường nền; thanh ngang không có đường nền nên căn tâm,
 * giống card/rect/image.) Phần tô mọc trái→phải tới value*w, cùng easing/thời gian với cột dọc.
 */
const HBarView: React.FC<ElProps<BarElement>> = ({r, s, t}) => {
	const el = r.el;
	const gp = easeOut(progress(t, el.growAt ?? r.enterAt, el.growDuration ?? 1.0));
	const v = clamp(el.value, 0, 1);
	const thick = Math.max(1, el.maxH);
	const fw = el.w * v * gp;
	// bo tròn như cột dọc (12px) nhưng không vượt nửa độ dày; đầu gốc (trái) bo nhỏ, đầu mọc (phải) bo lớn
	const rad = Math.min(12, thick / 2);
	const radBase = Math.min(4, rad);
	const valueSize = clamp(thick * 1.1, 20, 44);
	return (
		<div style={{position: 'absolute', left: -el.w / 2, top: -thick / 2, width: el.w, height: thick}}>
			<Wipe p={s.draw} bleedY={60}>
				{el.track !== null ? (
					<div
						style={{
							position: 'absolute',
							left: 0,
							top: 0,
							width: el.w,
							height: thick,
							background: el.track ?? 'rgba(29,36,51,0.06)',
							borderRadius: rad,
						}}
					/>
				) : null}
				<div
					style={{
						position: 'absolute',
						left: 0,
						top: 0,
						width: fw,
						height: thick,
						background: el.color ?? '#2F6FEB',
						borderRadius: `${radBase}px ${rad}px ${rad}px ${radBase}px`,
					}}
				/>
				{el.showValue ? (
					<div
						style={{
							position: 'absolute',
							left: el.w + 18,
							top: thick / 2,
							transform: 'translateY(-50%)',
							whiteSpace: 'nowrap',
							fontFamily: fontFamily(r.font),
							fontSize: valueSize,
							fontWeight: 800,
							color: el.valueColor ?? el.color ?? '#2F6FEB',
							opacity: clamp(gp * 3, 0, 1),
						}}
					>
						{formatVi(v * 100 * gp, 0)}%
					</div>
				) : null}
				{el.label ? (
					<div
						style={{
							position: 'absolute',
							left: 0,
							bottom: thick + 10,
							whiteSpace: 'nowrap',
							fontFamily: fontFamily(r.font),
							fontSize: 26,
							fontWeight: 600,
							color: el.labelColor ?? '#4A5263',
						}}
					>
						{el.label}
					</div>
				) : null}
			</Wipe>
		</div>
	);
};

// ---------------------------------------------------------------- path
export const PathView: React.FC<ElProps<PathElement>> = (props) => {
	if (props.r.geom.rough) return <RoughPathView {...props} />;
	return <PlainPathView {...props} />;
};

/**
 * Các nét rough.js lộ dần theo p (nét chính tuần tự theo độ dài; nét đè lộ cùng nhịp với nét chính
 * của nó). Nét đang vẽ dở dùng pathLength chuẩn hoá nên không phụ thuộc sai số đo độ dài.
 * `dash` (px) = nét đứt: khi đó lộ dần bằng mask để mẫu nét đứt không bị kéo giãn.
 */
const RoughStrokes: React.FC<{
	dr: RoughDrawing;
	p: number;
	stroke: string;
	sw: number;
	dash?: string;
	maskId: string;
}> = ({dr, p, stroke, sw, dash, maskId}) => {
	const fr = revealFractions(dr, p);
	const drawing = p < 1;
	const N = 1000;
	const reveal = (f: number) =>
		f >= 1 ? {} : {pathLength: N, strokeDasharray: `${N} ${N}`, strokeDashoffset: N * (1 - f)};
	const common = {fill: 'none', stroke, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const};
	const useMask = Boolean(dash) && drawing;
	return (
		<>
			{useMask ? (
				<defs>
					<mask id={maskId} maskUnits="userSpaceOnUse" x={-100000} y={-100000} width={200000} height={200000}>
						{dr.strokes.map((st, i) =>
							fr[i] > 0 ? (
								<React.Fragment key={i}>
									<path d={st.d} {...common} stroke="#fff" strokeWidth={sw + 6} {...reveal(fr[i])} />
									{st.d2 ? <path d={st.d2} {...common} stroke="#fff" strokeWidth={sw + 6} {...reveal(fr[i])} /> : null}
								</React.Fragment>
							) : null,
						)}
					</mask>
				</defs>
			) : null}
			{dr.strokes.map((st, i) => {
				if (fr[i] <= 0) return null;
				const dashed = dash && !st.solid;
				// nét đứt: chỉ vẽ nét chính (2 nét đứt chồng nhau trông rối)
				if (dashed) {
					return (
						<path
							key={i}
							d={st.d}
							{...common}
							strokeWidth={sw}
							strokeDasharray={dash}
							mask={useMask ? `url(#${maskId})` : undefined}
						/>
					);
				}
				const rv = reveal(fr[i]);
				return (
					<React.Fragment key={i}>
						<path d={st.d} {...common} strokeWidth={sw} {...rv} />
						{st.d2 ? <path d={st.d2} {...common} strokeWidth={sw * 0.8} opacity={0.9} {...rv} /> : null}
					</React.Fragment>
				);
			})}
		</>
	);
};

/** Path nét vẽ tay (timeline.rough / element.rough) — mũi tên = 2 ngạnh chữ V vẽ sau thân */
const RoughPathView: React.FC<ElProps<PathElement>> = ({r, s}) => {
	const el = r.el;
	const dr = r.geom.rough!;
	const maskId = useSafeId('rpm');
	const c = {x: r.geom.anchor.x - (el.x ?? 0), y: r.geom.anchor.y - (el.y ?? 0)};
	const p = s.draw ?? 1;
	const sw = el.strokeWidth ?? 6;
	const stroke = el.stroke ?? INK;
	const dash = el.dashed ? `${sw * 2.2} ${sw * 1.8}` : undefined;
	const drawing = s.draw !== null && p < 1;
	return (
		<svg width={1} height={1} style={{position: 'absolute', left: -c.x, top: -c.y, overflow: 'visible'}}>
			{el.fill ? <path d={el.d} fill={el.fill} stroke="none" opacity={drawing ? clamp((p - 0.7) / 0.3, 0, 1) : 1} /> : null}
			<RoughStrokes dr={dr} p={p} stroke={stroke} sw={sw} dash={dash} maskId={maskId} />
		</svg>
	);
};

const PlainPathView: React.FC<ElProps<PathElement>> = ({r, s}) => {
	const el = r.el;
	const info = r.geom.path!;
	const maskId = useSafeId('pm');
	// gốc toạ độ của path = (0,0) scene; khung đặt tại tâm bbox
	const c = {x: r.geom.anchor.x - (el.x ?? 0), y: r.geom.anchor.y - (el.y ?? 0)};
	const L = info.length;
	const p = s.draw ?? 1;
	const sw = el.strokeWidth ?? 6;
	const stroke = el.stroke ?? INK;
	const dash = el.dashed ? `${sw * 2.2} ${sw * 1.8}` : undefined;
	const drawing = s.draw !== null && p < 1;
	let arrow: string | null = null;
	if (el.arrow && L > 0) {
		const at = L * p;
		const size = sw * 3.2;
		if (at > size * 0.6) {
			const tip = info.pointAt(at);
			const back = info.pointAt(Math.max(0, at - size));
			const ang = Math.atan2(tip.y - back.y, tip.x - back.x);
			const p1 = {x: tip.x + Math.cos(ang) * sw * 0.5, y: tip.y + Math.sin(ang) * sw * 0.5};
			const l = {x: tip.x + Math.cos(ang + Math.PI - 0.45) * size, y: tip.y + Math.sin(ang + Math.PI - 0.45) * size};
			const rr = {x: tip.x + Math.cos(ang + Math.PI + 0.45) * size, y: tip.y + Math.sin(ang + Math.PI + 0.45) * size};
			arrow = `M${p1.x.toFixed(1)} ${p1.y.toFixed(1)} L${l.x.toFixed(1)} ${l.y.toFixed(1)} L${rr.x.toFixed(1)} ${rr.y.toFixed(1)} Z`;
		}
	}
	// khi vẽ: rút ngắn nét đi một chút để đầu mũi tên không bị nét tròn lòi ra
	const visibleLen = el.arrow ? Math.max(0, L * p - sw * 1.5) : L * p;
	return (
		<svg
			width={1}
			height={1}
			style={{position: 'absolute', left: -c.x, top: -c.y, overflow: 'visible'}}
		>
			{drawing && dash ? (
				<defs>
					<mask id={maskId} maskUnits="userSpaceOnUse" x={info.bbox.x - 50} y={info.bbox.y - 50} width={info.bbox.w + 100} height={info.bbox.h + 100}>
						<path d={el.d} fill="none" stroke="#fff" strokeWidth={sw + 4} strokeDasharray={`${L} ${L}`} strokeDashoffset={L - visibleLen} />
					</mask>
				</defs>
			) : null}
			{el.fill ? <path d={el.d} fill={el.fill} stroke="none" opacity={drawing ? clamp((p - 0.7) / 0.3, 0, 1) : 1} /> : null}
			<path
				d={el.d}
				fill="none"
				stroke={stroke}
				strokeWidth={sw}
				strokeLinecap="round"
				strokeLinejoin="round"
				strokeDasharray={dash ?? (drawing || el.arrow ? `${L} ${L}` : undefined)}
				strokeDashoffset={dash ? undefined : drawing || el.arrow ? L - visibleLen : undefined}
				mask={drawing && dash ? `url(#${maskId})` : undefined}
			/>
			{arrow ? <path d={arrow} fill={stroke} stroke={stroke} strokeWidth={sw * 0.6} strokeLinejoin="round" /> : null}
		</svg>
	);
};

// ---------------------------------------------------------------- rect / circle
export const ShapeView: React.FC<ElProps<ShapeElement>> = ({r, s}) => {
	const el = r.el;
	const box = r.geom.box;
	const outline = r.geom.outline!;
	const p = s.draw;
	const drawing = p !== null && p < 1;
	const fill = el.fill ?? '#2F6FEB';
	const sw = el.strokeWidth ?? (el.stroke ? 4 : 5);
	const stroke = el.stroke ?? (drawing ? fill : null);
	const fillOp = p === null ? 1 : clamp((p - 0.55) / 0.45, 0, 1);
	const labelOp = p === null ? 1 : clamp((p - 0.7) / 0.3, 0, 1);
	const L = outline.length;
	const dr = r.geom.rough;
	const roughId = useSafeId('rsm');
	const fitted = r.geom.label;
	const shape =
		el.type === 'circle' ? (
			<ellipse cx={0} cy={0} rx={box.w / 2} ry={box.h / 2} />
		) : (
			<rect x={box.ox} y={box.oy} width={box.w} height={box.h} rx={el.radius ?? 16} />
		);
	return (
		<>
			<svg width={1} height={1} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
				<g fill={fill} opacity={easeInOut(fillOp)}>{shape}</g>
				{stroke && dr ? (
					<RoughStrokes dr={dr} p={p ?? 1} stroke={stroke} sw={sw} maskId={roughId} />
				) : null}
				{stroke && !dr ? (
					<path
						d={polylineToD(outline.pts)}
						fill="none"
						stroke={stroke}
						strokeWidth={sw}
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeDasharray={drawing ? `${L} ${L}` : undefined}
						strokeDashoffset={drawing ? L * (1 - p!) : undefined}
					/>
				) : null}
			</svg>
			{el.label && fitted ? (
				<div
					style={{
						position: 'absolute',
						left: box.ox,
						top: box.oy,
						width: box.w,
						height: box.h,
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
						textAlign: 'center',
						padding: SHAPE_LABEL_PAD,
						boxSizing: 'border-box',
						fontFamily: fontFamily(r.font),
						fontSize: fitted.size,
						fontWeight: el.labelWeight ?? 600,
						color: el.labelColor ?? '#FFFFFF',
						lineHeight: 1.2,
						whiteSpace: 'pre',
						opacity: labelOp,
					}}
				>
					{fitted.lines.join('\n')}
				</div>
			) : null}
			{el.label && !fitted ? (
				<div
					style={{
						position: 'absolute',
						left: box.ox,
						top: box.oy,
						width: box.w,
						height: box.h,
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
						textAlign: 'center',
						padding: 12,
						boxSizing: 'border-box',
						fontFamily: fontFamily(r.font),
						fontSize: el.labelSize ?? 32,
						fontWeight: el.labelWeight ?? 600,
						color: el.labelColor ?? '#FFFFFF',
						lineHeight: 1.2,
						opacity: labelOp,
					}}
				>
					{el.label}
				</div>
			) : null}
		</>
	);
};

// ---------------------------------------------------------------- clock
export const ClockView: React.FC<ElProps<ClockElement>> = ({r, s, t}) => {
	const el = r.el;
	const R = el.r;
	const color = el.color ?? INK;
	const start = el.spinAt ?? r.enterAt + r.enterDur;
	const hour = lerp(el.fromHour, el.toHour, easeInOut(progress(t, start, el.spinDuration ?? 2)));
	const minuteAngle = hour * 360; // kim phút quay đủ vòng theo số giờ
	const hourAngle = hour * 30;
	const p = s.draw;
	const drawing = p !== null && p < 1;
	const L = 2 * Math.PI * R;
	const detailOp = p === null ? 1 : clamp((p - 0.6) / 0.4, 0, 1);
	const hand = (ang: number, len: number, w: number, c: string) => {
		const a = ((ang - 90) * Math.PI) / 180;
		return (
			<line x1={0} y1={0} x2={Math.cos(a) * len} y2={Math.sin(a) * len} stroke={c} strokeWidth={w} strokeLinecap="round" />
		);
	};
	return (
		<svg width={1} height={1} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
			<circle cx={0} cy={0} r={R} fill={el.face ?? '#FFFFFF'} opacity={drawing ? detailOp : 1} />
			<circle
				cx={0}
				cy={0}
				r={R}
				fill="none"
				stroke={color}
				strokeWidth={R * 0.07}
				transform="rotate(-90)"
				strokeDasharray={drawing ? `${L} ${L}` : undefined}
				strokeDashoffset={drawing ? L * (1 - p!) : undefined}
			/>
			<g opacity={detailOp}>
				{Array.from({length: 12}).map((_, i) => {
					const a = (i / 12) * Math.PI * 2;
					const r1 = R * (i % 3 === 0 ? 0.74 : 0.8);
					return (
						<line
							key={i}
							x1={Math.cos(a) * r1}
							y1={Math.sin(a) * r1}
							x2={Math.cos(a) * R * 0.88}
							y2={Math.sin(a) * R * 0.88}
							stroke={color}
							strokeWidth={R * (i % 3 === 0 ? 0.05 : 0.03)}
							strokeLinecap="round"
						/>
					);
				})}
				{hand(hourAngle, R * 0.5, R * 0.08, color)}
				{hand(minuteAngle, R * 0.72, R * 0.05, color)}
				<circle cx={0} cy={0} r={R * 0.08} fill={el.accent ?? '#F2611D'} />
			</g>
		</svg>
	);
};

// ---------------------------------------------------------------- caption (TikTok: phụ đề karaoke đốt sẵn)
export const CaptionView: React.FC<ElProps<CaptionElement>> = ({r, t}) => {
	const el = r.el;
	const box = r.geom.box;
	const size = el.size ?? 46;
	const weight = el.weight ?? 800;
	return (
		<div
			style={{
				position: 'absolute',
				left: box.ox,
				top: box.oy,
				width: box.w,
				display: 'flex',
				flexWrap: 'wrap',
				justifyContent: 'center',
				alignContent: 'center',
				gap: `${size * 0.1}px ${size * 0.28}px`,
				background: el.bg ?? 'rgba(29,36,51,0.82)',
				borderRadius: 16,
				padding: `${size * 0.3}px ${size * 0.4}px`,
				boxSizing: 'border-box',
			}}
		>
			{el.words.map((w, i) => {
				const active = t >= w.start && t < w.end;
				return (
					<span
						key={i}
						style={{
							fontFamily: fontFamily(r.font),
							fontSize: size,
							fontWeight: weight,
							lineHeight: 1.15,
							color: active ? (el.activeColor ?? ORANGE) : (el.color ?? '#FFFFFF'),
							whiteSpace: 'pre',
							...(el.outline
								? {WebkitTextStroke: `${Math.round(size * 0.09)}px ${el.outline}`, paintOrder: 'stroke fill'}
								: {}),
							...(el.activeScale && active
								? {transform: `scale(${el.activeScale})`, display: 'inline-block'}
								: {display: 'inline-block'}),
						}}
					>
						{w.text}
					</span>
				);
			})}
		</div>
	);
};
