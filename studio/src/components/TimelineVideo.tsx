import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, Html5Audio, interpolate, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT_SANS, fontsReady, loadFonts} from '../fonts';
import {resolveAsset} from '../lib/assets';
import type {Ctx} from '../lib/resolve';
import {DEFAULT_BOWING, DEFAULT_ROUGHNESS} from '../lib/rough';
import type {VideoProps} from '../types';
import {Hud} from './Hud';
import {Board, SceneStack} from './Renderers';

/** Giữ render cho tới khi font (kể cả subset tiếng Việt) đã nạp xong */
const useFonts = () => {
	const [ok, setOk] = useState(fontsReady());
	const [handle] = useState(() => (fontsReady() ? null : delayRender('fonts')));
	useEffect(() => {
		if (handle === null) return;
		loadFonts()
			.then(() => {
				setOk(true);
				continueRender(handle);
			})
			.catch((e) => cancelRender(e));
	}, [handle]);
	return ok;
};

export const TimelineVideo: React.FC<VideoProps> = ({videoId, timelineFile, timeline, imageSizes, traces, error}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const fontsOk = useFonts();
	const ctx: Ctx | null = useMemo(
		() =>
			timeline
				? {
						videoId,
						style: timeline.style,
						fps,
						imageSizes: imageSizes ?? {},
						traces: traces ?? {},
						defaultFont: timeline.font ?? (timeline.style === 'C' ? 'hand' : 'sans'),
						rough: {
							enabled: timeline.rough === true,
							roughness: timeline.roughness ?? DEFAULT_ROUGHNESS,
							bowing: timeline.bowing ?? DEFAULT_BOWING,
						},
						fitText: timeline.fitText === true,
					}
				: null,
		[videoId, timeline, fps, imageSizes, traces],
	);
	if (!timeline || !ctx) {
		return (
			<AbsoluteFill
				style={{
					background: '#F7F8FA',
					alignItems: 'center',
					justifyContent: 'center',
					fontFamily: FONT_SANS,
					color: '#1D2433',
					textAlign: 'center',
					padding: 120,
				}}
			>
				<div style={{fontSize: 56, fontWeight: 800}}>Chưa có timeline</div>
				<div style={{fontSize: 30, marginTop: 24, color: '#4A5263'}}>
					public/{videoId}/{timelineFile}
				</div>
				{error ? <div style={{fontSize: 24, marginTop: 24, color: '#C2410C'}}>{error}</div> : null}
			</AbsoluteFill>
		);
	}
	const t = frame / fps;
	return (
		<AbsoluteFill style={{background: timeline.background ?? (timeline.style === 'C' ? '#FCFCFA' : '#F7F8FA')}}>
			{timeline.audio ? (
				<Html5Audio src={resolveAsset(videoId, timeline.audio)} volume={timeline.audioVolume ?? 1} />
			) : null}
			{timeline.music ? (
				<Html5Audio
					src={resolveAsset(videoId, timeline.music.src)}
					loop
					volume={(f) => {
						// nhạc nền: lên dần ở đầu, tắt dần ở cuối video (0019)
						const m = timeline.music!;
						const v = m.volume ?? 0.15;
						const tt = f / fps;
						const vao = m.fadeIn ? Math.min(1, tt / m.fadeIn) : 1;
						const ra = m.fadeOut ? interpolate(tt, [timeline.duration - m.fadeOut, timeline.duration], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
						return v * vao * ra;
					}}
				/>
			) : null}
			{(timeline.sfx ?? []).map((c, i) => (
				<Sequence key={`sfx-${i}`} from={Math.max(0, Math.round(c.at * fps))} durationInFrames={Math.round(2 * fps)} layout="none">
					<Html5Audio src={resolveAsset(videoId, c.src)} volume={c.volume ?? 0.35} />
				</Sequence>
			))}
			{timeline.style === 'C' ? (
				<Board tl={timeline} ctx={ctx} t={t} fontsOk={fontsOk} />
			) : (
				<SceneStack tl={timeline} ctx={ctx} t={t} fontsOk={fontsOk} />
			)}
			{timeline.hud ? <Hud hud={timeline.hud} videoId={videoId} t={t} /> : null}
		</AbsoluteFill>
	);
};
