import type {CalculateMetadataFunction} from 'remotion';
import {staticFile} from 'remotion';
import type {ImageSizes, Timeline, TraceData, TraceMap, VideoProps} from '../types';
import {resolveAsset} from './assets';
import {traceUrls} from './trace';
import {validateTimeline} from './validate';

const loadSize = (url: string) =>
	new Promise<{w: number; h: number} | null>((resolve) => {
		const img = new Image();
		img.onload = () => resolve({w: img.naturalWidth, h: img.naturalHeight});
		img.onerror = () => resolve(null);
		img.src = url;
	});

/** Đọc kích thước thật của mọi ảnh (để tính h theo tỉ lệ và vẽ mask) */
const collectImageSizes = async (tl: Timeline, videoId: string) => {
	const urls = new Set<string>();
	if (tl.hand?.src) urls.add(resolveAsset(videoId, tl.hand.src));
	for (const s of tl.scenes) {
		for (const e of s.elements) {
			if (e.type === 'image') urls.add(resolveAsset(videoId, e.src));
			if (e.type === 'card' && e.icon) urls.add(resolveAsset(videoId, e.icon));
		}
	}
	// trace map: ảnh có trace=true cần <src>.trace.png + .trace.json
	const traceSrcs = new Set<string>();
	for (const s of tl.scenes) {
		for (const e of s.elements) {
			if (e.type === 'image' && e.trace) traceSrcs.add(e.src);
		}
	}
	for (const src of traceSrcs) urls.add(resolveAsset(videoId, traceUrls(src).png));
	const sizes: ImageSizes = {};
	const missing: string[] = [];
	await Promise.all(
		[...urls].map(async (u) => {
			const s = await loadSize(u);
			if (s) sizes[u] = s;
			else missing.push(u);
		}),
	);
	const traces: TraceMap = {};
	await Promise.all(
		[...traceSrcs].map(async (src) => {
			const u = resolveAsset(videoId, traceUrls(src).json);
			try {
				const res = await fetch(u);
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const data = (await res.json()) as TraceData;
				if (!Array.isArray(data.path) || !(data.width > 0) || !(data.height > 0))
					throw new Error('thiếu width/height/path');
				traces[resolveAsset(videoId, src)] = data;
			} catch (e) {
				missing.push(`${u} (${(e as Error).message})`);
			}
		}),
	);
	return {sizes, missing, traces};
};

export const calculateTimelineMetadata: CalculateMetadataFunction<VideoProps> = async ({
	props,
	abortSignal,
	isRendering,
}) => {
	const path = `${props.videoId}/${props.timelineFile}`;
	const fallback = (error: string) => {
		if (isRendering) throw new Error(`[timeline] ${path}: ${error}`);
		return {durationInFrames: 150, fps: 30, width: 1920, height: 1080, props: {...props, timeline: null, error}};
	};
	let tl: Timeline;
	let res: Response;
	try {
		res = await fetch(staticFile(path), {signal: abortSignal});
	} catch (e) {
		return fallback(`Không đọc được: ${(e as Error).message}`);
	}
	if (!res.ok) return fallback(`HTTP ${res.status} (chưa có file?)`);
	try {
		tl = (await res.json()) as Timeline;
	} catch (e) {
		return fallback(`JSON lỗi: ${(e as Error).message}`);
	}
	const errs = validateTimeline(tl);
	if (errs.length) return fallback(`Timeline lỗi:\n- ${errs.slice(0, 12).join('\n- ')}`);
	const {sizes, missing, traces} = await collectImageSizes(tl, props.videoId);
	if (missing.length) {
		const msg = `Thiếu ảnh/trace: ${missing.join(', ')}`;
		if (isRendering) throw new Error(`[timeline] ${path}: ${msg}`);
		console.warn(msg);
	}
	const fps = tl.fps || 30;
	return {
		durationInFrames: Math.max(1, Math.round(tl.duration * fps)),
		fps,
		width: tl.width || 1920,
		height: tl.height || 1080,
		props: {...props, timeline: tl, imageSizes: sizes, traces, error: null},
	};
};
