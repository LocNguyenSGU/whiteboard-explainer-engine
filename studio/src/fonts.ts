// Font được bundle cục bộ qua @fontsource (không cần mạng khi render).
// Mỗi file CSS chứa đủ subset latin / latin-ext / vietnamese (unicode-range).
import '@fontsource/be-vietnam-pro/400.css';
import '@fontsource/be-vietnam-pro/600.css';
import '@fontsource/be-vietnam-pro/800.css';
import '@fontsource/mali/400.css';
import '@fontsource/mali/600.css';
import '@fontsource/mali/700.css';
import type {FontKind} from './types';

export const FONT_SANS = '"Be Vietnam Pro", "Helvetica Neue", Arial, sans-serif';
export const FONT_HAND = '"Mali", "Be Vietnam Pro", cursive';

export const fontFamily = (kind: FontKind) =>
	kind === 'hand' ? FONT_HAND : FONT_SANS;

// Mẫu có đủ ký tự latin + latin-ext + tiếng Việt để kéo về mọi subset
const SAMPLE = 'AaBb 0123 Đđ Ăă Ơơ Ưư ẠạẶặỠỡỮữ ếộ — %';
const FACES = [
	'400 40px "Be Vietnam Pro"',
	'600 40px "Be Vietnam Pro"',
	'800 40px "Be Vietnam Pro"',
	'400 40px "Mali"',
	'600 40px "Mali"',
	'700 40px "Mali"',
];

let ready = false;
let promise: Promise<void> | null = null;

export const loadFonts = (): Promise<void> => {
	if (!promise) {
		promise = Promise.all(FACES.map((f) => document.fonts.load(f, SAMPLE)))
			.then(() => document.fonts.ready)
			.then(() => {
				ready = true;
			});
	}
	return promise;
};

export const fontsReady = () => ready;
