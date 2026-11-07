// Tự co chữ vừa khung (opt-in): đo bằng font thật (layoutText/measureWidth), cho xuống dòng
// trong khung trước, rồi giảm cỡ chữ từng bước tới sàn 60% cỡ yêu cầu. Kết quả xác định + có cache.
import {fontsReady} from '../fonts';
import type {FontKind} from '../types';
import {layoutText} from './text-layout';

/** Sàn co chữ: 60% cỡ yêu cầu */
export const FIT_MIN_SCALE = 0.6;
/** Số bước giảm cỡ từ 100% xuống 60% (mỗi bước 2.5%) */
const FIT_STEPS = 16;

export interface FitBlock {
	text: string;
	size: number;
	weight: number;
	lineHeight: number;
}

export interface FittedBlock {
	size: number;
	lines: string[];
	/** chiều cao khối = số dòng × size × lineHeight */
	height: number;
	/** dòng rộng nhất (px) */
	width: number;
}

export interface FitResult {
	/** hệ số co đã dùng (1 = giữ nguyên) */
	scale: number;
	blocks: FittedBlock[];
}

const cache = new Map<string, FitResult>();

const layBlock = (b: FitBlock, k: number, font: FontKind, maxW: number): FittedBlock => {
	const size = b.size * k;
	const lay = layoutText(b.text, size, b.weight, font, maxW, b.lineHeight);
	return {size, lines: lay.lines.map((l) => l.text), height: lay.height, width: lay.width};
};

/**
 * Co các khối chữ (cùng một hệ số) để vừa vùng maxW × maxH.
 * `gap` = khoảng cách cố định giữa các khối (px, không co). `maxLines` (tuỳ chọn) giới hạn số dòng mỗi khối.
 * Không vừa ở 60% → trả về 60% (cho tràn).
 */
export const fitBlocks = (
	blocks: FitBlock[],
	font: FontKind,
	maxW: number,
	maxH: number,
	gap = 0,
	maxLines?: number,
): FitResult => {
	const key = [
		font,
		maxW.toFixed(2),
		maxH.toFixed(2),
		gap,
		maxLines ?? 0,
		...blocks.map((b) => `${b.text}\u0001${b.size}\u0001${b.weight}\u0001${b.lineHeight}`),
	].join('\u0002');
	const hit = cache.get(key);
	if (hit) return hit;
	const w = Math.max(1, maxW);
	let res: FitResult | null = null;
	for (let i = 0; i <= FIT_STEPS; i++) {
		const k = 1 - ((1 - FIT_MIN_SCALE) * i) / FIT_STEPS;
		const laid = blocks.map((b) => layBlock(b, k, font, w));
		const h = laid.reduce((a, b) => a + b.height, 0) + gap * Math.max(0, laid.length - 1);
		const ok =
			h <= maxH + 0.5 &&
			laid.every((b) => b.width <= w + 0.5 && (maxLines === undefined || b.lines.length <= maxLines));
		res = {scale: k, blocks: laid};
		if (ok) break;
	}
	// Chỉ cache khi font thật đã nạp (giống layoutText)
	if (fontsReady()) cache.set(key, res!);
	return res!;
};
