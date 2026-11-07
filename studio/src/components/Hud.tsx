import React from 'react';
import {Img} from 'remotion';
import {FONT_SANS} from '../fonts';
import {resolveAsset} from '../lib/assets';
import {clamp, easeOut, progress} from '../lib/math';
import type {Hud as HudT} from '../types';

// Thanh định vị cố định ngoài camera (khuôn "giải thích sự kiện", 0019): vật xuyên suốt + nhãn chương góc trên trái,
// trục mốc phía trên có chấm hiện dần, mốc hiện tại tô cam + nhãn. Màu theo thương hiệu nền sáng.
const INK = '#1D2433';
const INK2 = '#5B6474';
const LINE = '#D5D9E0';
const BORDER = '#E3E6EB';
const ORANGE = '#F2611D';
const X0 = 560;
const X1 = 1760;
const Y = 48;

const Pill: React.FC<{text: string; x: number; y: number; size: number; color: string; opacity: number; dy?: number; center?: boolean}> = ({
	text,
	x,
	y,
	size,
	color,
	opacity,
	dy = 0,
	center,
}) => (
	<div
		style={{
			position: 'absolute',
			left: x,
			top: y + dy,
			transform: center ? 'translateX(-50%)' : undefined,
			opacity,
			padding: `${Math.round(size * 0.28)}px ${Math.round(size * 0.65)}px`,
			background: '#FFFFFF',
			border: `2px solid ${BORDER}`,
			borderRadius: 10,
			fontFamily: FONT_SANS,
			fontWeight: 600,
			fontSize: size,
			color,
			whiteSpace: 'nowrap',
			boxShadow: '0 1px 2px rgba(29,36,51,0.06)',
		}}
	>
		{text}
	</div>
);

/** Phần tử cuối cùng có at <= t, và phần tử trước nó */
const hienTai = <T extends {at: number}>(xs: T[], t: number): [T | null, T | null] => {
	let cur: T | null = null;
	let prev: T | null = null;
	for (const x of xs) {
		if (x.at <= t) {
			prev = cur;
			cur = x;
		}
	}
	return [cur, prev];
};

// Mục lục header cho video tuần (gop-y 25/10/2026): các mục chia đều bề ngang, mục đã qua chữ đậm, mục đang nói
// chữ cam + gạch chân chạy theo tiến độ, mục sắp tới chữ mờ. Luôn hiện, để người xem biết đang ở đâu.
const MucLuc: React.FC<{muc: {at: number; label: string}[]; end: number; t: number}> = ({muc, end, t}) => {
	const L = 60;
	const R = 1860;
	const w = (R - L) / muc.length;
	const vao = easeOut(progress(t, 0, 0.6));
	return (
		<div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 96, opacity: vao, pointerEvents: 'none'}}>
			<div style={{position: 'absolute', left: L, top: 74, width: R - L, height: 3, background: LINE, borderRadius: 2}} />
			{muc.map((m, i) => {
				const tiep = i + 1 < muc.length ? muc[i + 1].at : end;
				const dang = t >= m.at && t < tiep;
				const qua = t >= tiep;
				const p = dang ? clamp((t - m.at) / Math.max(0.1, tiep - m.at), 0, 1) : qua ? 1 : 0;
				return (
					<React.Fragment key={i}>
						<div
							style={{
								position: 'absolute',
								left: L + i * w,
								top: 26,
								width: w,
								textAlign: 'center',
								fontFamily: FONT_SANS,
								fontWeight: dang ? 800 : 600,
								fontSize: 25,
								color: dang ? ORANGE : qua ? INK : INK2,
								opacity: dang || qua ? 1 : 0.55,
								whiteSpace: 'nowrap',
							}}
						>
							{m.label}
						</div>
						<div
							style={{
								position: 'absolute',
								left: L + i * w + 6,
								top: 72,
								width: Math.max(0, (w - 12) * p),
								height: 7,
								borderRadius: 4,
								background: dang ? ORANGE : INK2,
								opacity: dang ? 1 : 0.35,
							}}
						/>
					</React.Fragment>
				);
			})}
		</div>
	);
};

export const Hud: React.FC<{hud: HudT; videoId: string; t: number}> = ({hud, videoId, t}) => {
	if (hud.mucLuc && hud.mucLuc.length) {
		return <MucLuc muc={[...hud.mucLuc].sort((a, b) => a.at - b.at)} end={hud.end ?? Infinity} t={t} />;
	}
	const chapters = [...hud.chapters].sort((a, b) => a.at - b.at);
	const marks = [...hud.marks].sort((a, b) => a.at - b.at);
	const start = hud.start ?? Math.min(chapters[0]?.at ?? Infinity, marks[0]?.at ?? Infinity);
	if (!Number.isFinite(start) || t < start) return null;
	const vao = easeOut(progress(t, start, 0.5));

	const [ch, chPrev] = hienTai(chapters, t);
	const pCh = ch ? easeOut(progress(t, ch.at, 0.4)) : 0;
	const xNhan = hud.icon ? 128 : 48;

	const [mk] = hienTai(marks, t);
	const pTruc = easeOut(progress(t, start, 0.9));
	return (
		<div style={{position: 'absolute', inset: 0, opacity: vao, pointerEvents: 'none'}}>
			{hud.icon ? (
				<Img
					src={resolveAsset(videoId, hud.icon)}
					style={{position: 'absolute', left: 40, top: 22, width: 68, height: 68, objectFit: 'contain'}}
				/>
			) : null}
			{chPrev && pCh < 1 ? <Pill text={chPrev.label} x={xNhan} y={32} size={24} color={INK2} opacity={1 - pCh} dy={-10 * pCh} /> : null}
			{ch ? <Pill text={ch.label} x={xNhan} y={32} size={24} color={INK2} opacity={pCh} dy={10 * (1 - pCh)} /> : null}
			{marks.length ? (
				<svg width={1920} height={140} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
					<line x1={X0} y1={Y} x2={X0 + (X1 - X0) * pTruc} y2={Y} stroke={LINE} strokeWidth={3} strokeLinecap="round" />
					{marks
						.filter((m) => m.at <= t)
						.map((m, i) => {
							const x = X0 + (X1 - X0) * clamp(m.pos, 0, 1);
							const laHienTai = m === mk;
							const p = easeOut(progress(t, m.at, 0.35));
							// nảy nhẹ khi chấm mới hiện
							const nay = laHienTai ? 1 + 0.5 * Math.sin(Math.PI * clamp(progress(t, m.at, 0.35), 0, 1)) : 1;
							const r = (laHienTai ? 10 : 6) * p * nay;
							return <circle key={i} cx={x} cy={Y} r={r} fill={laHienTai ? ORANGE : INK2} />;
						})}
				</svg>
			) : null}
			{mk ? (
				<Pill
					text={mk.label}
					x={X0 + (X1 - X0) * clamp(mk.pos, 0, 1)}
					y={68}
					size={22}
					color={INK}
					opacity={easeOut(progress(t, mk.at, 0.4))}
					center
				/>
			) : null}
		</div>
	);
};
