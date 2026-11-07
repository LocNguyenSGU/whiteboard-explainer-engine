// Data contract cho timeline JSON. Mọi thời gian là GIÂY TUYỆT ĐỐI trong video.
// Toạ độ: không gian scene 1920x1080 (style C: cộng thêm scene.origin trên board).

export type Style = 'A' | 'B' | 'C';

export type EnterType =
	| 'pop'
	| 'slide-up'
	| 'slide-left'
	| 'slide-right'
	| 'fade'
	| 'draw'
	| 'grow'
	| 'none';

export type ExitType = 'fade' | 'slide-down' | 'shrink' | 'none';

export type TransitionType =
	| 'none'
	| 'fade'
	| 'push-left'
	| 'push-up'
	| 'zoom-from'
	| 'pan';

export interface Vec {
	x: number;
	y: number;
}

export interface CameraKey {
	at: number;
	x: number;
	y: number;
	scale?: number;
}

export interface Move {
	at: number;
	x?: number;
	y?: number;
	scale?: number;
	rotate?: number;
	opacity?: number;
	duration?: number;
}

export interface GrayscaleAnim {
	at: number;
	to: number;
	duration?: number;
}

export interface TransitionIn {
	type: TransitionType;
	duration?: number;
	/** zoom-from: id của element ở scene TRƯỚC để zoom vào */
	fromElement?: string;
	/** pan (style C): mức zoom-out ở giữa quãng pan (0..0.5). Mặc định 0.12 */
	dip?: number;
}

interface BaseElement {
	id: string;
	x?: number;
	y?: number;
	enterAt?: number;
	enter?: EnterType;
	enterDuration?: number;
	hand?: boolean;
	exitAt?: number;
	exit?: ExitType;
	exitDuration?: number;
	moves?: Move[];
	/** mở rộng: opacity/scale/rotate gốc, z-index */
	opacity?: number;
	scale?: number;
	rotate?: number;
	z?: number;
	/** rung liên tục khi đang hiện (nhân vật hoạt hình, plan/16) — dao động nhỏ, không cần khai moves từng khung */
	idle?: {type: 'rung'; amplitude?: number; speed?: number; scaleAmp?: number};
}

export interface ImageElement extends BaseElement {
	type: 'image';
	src: string;
	w: number;
	/** mở rộng: nếu bỏ trống thì tính từ tỉ lệ ảnh */
	h?: number;
	tint?: string | {color: string; amount?: number} | null;
	grayscale?: GrayscaleAnim | null;
	flipX?: boolean;
	/** khi enter = draw: vẽ theo trace map <src>.trace.png/.trace.json (tạo offline) */
	trace?: boolean;
	/** đoạn video thật (ghi màn hình…) phát trong khung ảnh, bắt đầu lúc enterAt; `src` là khung đại diện để lấy kích thước */
	video?: string;
	videoRate?: number;
}

export type FontKind = 'sans' | 'hand';

export interface TextElement extends BaseElement {
	type: 'text';
	text: string;
	size?: number;
	weight?: number;
	color?: string;
	align?: 'left' | 'center' | 'right';
	maxWidth?: number;
	box?: 'none' | 'card' | 'pill';
	boxColor?: string;
	lineHeight?: number;
	font?: FontKind;
	/** tự co chữ khi vượt maxWidth/maxLines (ghi đè timeline.fitText). Cần maxWidth */
	fit?: boolean;
	/** dùng với fit: số dòng tối đa trước khi co chữ. Mặc định 2 */
	maxLines?: number;
	/** khoanh tròn hoặc gạch chân cả khối chữ bằng nét tay rough.js, hiện ra sau khi chữ hiện xong (cần timeline.rough bật) */
	mark?: 'khoanh' | 'gach_chan';
	markColor?: string;
	markWidth?: number;
	/** ghi đè timeline.rough cho riêng nét khoanh/gạch chân (false = tắt dù timeline.rough bật) */
	rough?: boolean;
}

export interface CounterElement extends BaseElement {
	type: 'counter';
	from: number;
	to: number;
	decimals?: number;
	prefix?: string;
	suffix?: string;
	size?: number;
	weight?: number;
	color?: string;
	countAt?: number;
	countDuration?: number;
	font?: FontKind;
	/** mặc định true: phân cách hàng nghìn bằng dấu chấm */
	thousands?: boolean;
}

export interface CardElement extends BaseElement {
	type: 'card';
	w: number;
	h: number;
	title?: string;
	body?: string;
	icon?: string;
	color?: string;
	border?: string;
	accent?: string;
	titleColor?: string;
	bodyColor?: string;
	titleSize?: number;
	bodySize?: number;
	radius?: number;
	flipIn?: boolean;
	font?: FontKind;
	/** tự co title/body cho vừa thẻ (ghi đè timeline.fitText) */
	fit?: boolean;
	/** nét viền vẽ tay rough.js thay viền thẳng (ghi đè timeline.rough) */
	rough?: boolean;
}

export interface BarElement extends BaseElement {
	type: 'bar';
	w: number;
	maxH: number;
	value: number;
	color?: string;
	track?: string | null;
	label?: string;
	labelColor?: string;
	showValue?: boolean;
	valueColor?: string;
	growAt?: number;
	growDuration?: number;
	font?: FontKind;
	/**
	 * Thanh tiến độ nằm ngang. Mặc định (false/bỏ trống) là cột dọc neo ở đáy-giữa (x,y).
	 * Khi true: rãnh dài `w`, dày `maxH`, TÂM rãnh tại (x,y); phần tô mọc trái→phải tới value*w.
	 * showValue hiện % bên phải rãnh, label hiện phía trên mép trái rãnh.
	 */
	horizontal?: boolean;
}

export interface PathElement extends BaseElement {
	type: 'path';
	d: string;
	stroke?: string;
	strokeWidth?: number;
	arrow?: boolean;
	fill?: string | null;
	dashed?: boolean;
	/** nét vẽ tay rough.js (ghi đè timeline.rough) */
	rough?: boolean;
}

export interface ShapeElement extends BaseElement {
	type: 'rect' | 'circle';
	w?: number;
	h?: number;
	r?: number;
	fill?: string;
	stroke?: string | null;
	strokeWidth?: number;
	radius?: number;
	label?: string;
	labelColor?: string;
	labelSize?: number;
	labelWeight?: number;
	font?: FontKind;
	/** nét viền vẽ tay rough.js (ghi đè timeline.rough) */
	rough?: boolean;
	/** tự co label cho vừa khung (ghi đè timeline.fitText) */
	fit?: boolean;
}

export interface CaptionWord {
	text: string;
	start: number;
	end: number;
}

/** Phụ đề đốt sẵn vào hình kiểu karaoke (chữ đang đọc nổi bật) — dùng cho TikTok, không dùng cho YouTube
 * (kênh tải phụ đề rời, không in lên hình). */
export interface CaptionElement extends BaseElement {
	type: 'caption';
	words: CaptionWord[];
	x: number;
	y: number;
	maxWidth?: number;
	size?: number;
	weight?: number;
	color?: string;
	activeColor?: string;
	bg?: string;
	font?: FontKind;
	/** viền chữ (màu) — chữ trắng viền mực đọc được trên mọi nền, kiểu phụ đề Shorts nước ngoài (doc.py bố cục 2) */
	outline?: string;
	/** phóng to chữ đang đọc (vd. 1.12) */
	activeScale?: number;
}

export interface ClockElement extends BaseElement {
	type: 'clock';
	r: number;
	fromHour: number;
	toHour: number;
	spinAt?: number;
	spinDuration?: number;
	face?: string;
	color?: string;
	accent?: string;
}

export type TimelineElement =
	| ImageElement
	| TextElement
	| CounterElement
	| CardElement
	| BarElement
	| PathElement
	| ShapeElement
	| ClockElement
	| CaptionElement;

export interface Scene {
	id: string;
	start: number;
	end: number;
	origin?: Vec;
	transitionIn?: TransitionIn;
	camera?: CameraKey[];
	/** mở rộng: nền riêng cho scene (A/B) */
	background?: string;
	elements: TimelineElement[];
}

export interface SfxCue {
	src: string;
	at: number;
	volume?: number;
}

export interface Hud {
	/** giây HUD bắt đầu hiện (mặc định: mốc chương đầu tiên) */
	start?: number;
	/** ảnh nhỏ của vật xuyên suốt, góc trên trái */
	icon?: string | null;
	/** nhãn chương góc trên trái, đổi theo `at` */
	chapters: {at: number; label: string}[];
	/** trục mốc phía trên: chấm hiện dần theo `at`, `pos` 0..1 dọc trục */
	marks: {at: number; label: string; pos: number}[];
	/** mục lục cố định ở header (video tuần): hiện đủ các mục từ đầu, mục đang nói tô cam + thanh tiến độ trong mục */
	mucLuc?: {at: number; label: string}[];
	/** giây kết thúc mục cuối (thường = thời lượng video) */
	end?: number;
}

export interface HandConfig {
	src: string;
	tip: Vec;
	scale?: number;
}

export interface Timeline {
	style: Style;
	fps: number;
	width: number;
	height: number;
	duration: number;
	audio?: string | null;
	/** mở rộng */
	audioVolume?: number;
	music?: {src: string; volume?: number; fadeIn?: number; fadeOut?: number} | null;
	/** tiếng hiệu ứng đặt theo mốc giây (khuôn "giải thích sự kiện", 0019) */
	sfx?: SfxCue[];
	/** thanh định vị cố định ngoài camera: vật xuyên suốt + nhãn chương + trục mốc (0019) */
	hud?: Hud | null;
	background?: string;
	hand?: HandConfig | null;
	board?: {width: number; height: number} | null;
	/** mở rộng: chữ mặc định 'sans' (A/B) hoặc 'hand' (C) */
	font?: FontKind;
	/** mở rộng: bật/tắt nhiễu giấy (mặc định true ở style C) */
	paperNoise?: boolean;
	/** thử nghiệm tốc độ: nhiễu giấy đứng yên, không trôi theo camera */
	noiseStatic?: boolean;
	/** mở rộng: nét vẽ tay rough.js cho rect/circle/path (mặc định false = nét hình học như cũ) */
	rough?: boolean;
	/** độ run tay rough.js, mặc định 1.2 (0 = thẳng) */
	roughness?: number;
	/** độ võng đoạn thẳng rough.js, mặc định 1 */
	bowing?: number;
	/** mở rộng: tự co chữ vừa khung cho label rect/circle, title/body card, text có maxWidth (mặc định false) */
	fitText?: boolean;
	scenes: Scene[];
}

export interface ImageSize {
	w: number;
	h: number;
}

export type ImageSizes = Record<string, ImageSize>;

/** Nội dung <asset>.trace.json: path = [[t, x, y], ...] theo pixel ảnh, t tăng dần 0..1 */
export interface TraceData {
	width: number;
	height: number;
	outlineEnd?: number;
	path: [number, number, number][];
}

/** key = URL đã resolve của ảnh gốc (.png) */
export type TraceMap = Record<string, TraceData>;

export type VideoProps = {
	videoId: string;
	timelineFile: string;
	/** được điền bởi calculateMetadata */
	timeline?: Timeline | null;
	imageSizes?: ImageSizes;
	traces?: TraceMap;
	error?: string | null;
};
