import type {Timeline, TimelineElement} from '../types';

const ELEMENT_TYPES = ['image', 'text', 'counter', 'card', 'bar', 'path', 'rect', 'circle', 'clock', 'caption'];
const ENTERS = ['pop', 'slide-up', 'slide-left', 'slide-right', 'fade', 'draw', 'grow', 'none'];
const EXITS = ['fade', 'slide-down', 'shrink', 'none'];
const TRANSITIONS = ['none', 'fade', 'push-left', 'push-up', 'zoom-from', 'pan'];

const REQUIRED: Record<string, string[]> = {
	image: ['src', 'w', 'x', 'y'],
	text: ['text', 'x', 'y'],
	counter: ['from', 'to', 'x', 'y'],
	card: ['w', 'h', 'x', 'y'],
	bar: ['w', 'maxH', 'value', 'x', 'y'],
	path: ['d'],
	rect: ['x', 'y'],
	circle: ['x', 'y'],
	clock: ['r', 'fromHour', 'toHour', 'x', 'y'],
	caption: ['words', 'x', 'y'],
};

/** Kiểm tra nhẹ timeline, trả về danh sách lỗi (rỗng = hợp lệ) */
export const validateTimeline = (tl: Timeline): string[] => {
	const errs: string[] = [];
	if (!tl || typeof tl !== 'object') return ['timeline không phải object'];
	if (!['A', 'B', 'C'].includes(tl.style)) errs.push(`style không hợp lệ: ${tl.style}`);
	if (!(tl.duration > 0)) errs.push('duration phải > 0');
	if (!Array.isArray(tl.scenes) || tl.scenes.length === 0) errs.push('scenes rỗng');
	if (tl.hand && (!tl.hand.src || !tl.hand.tip)) errs.push('hand cần src và tip');
	if (tl.rough !== undefined && typeof tl.rough !== 'boolean') errs.push(`rough phải là boolean (${String(tl.rough)})`);
	if (tl.fitText !== undefined && typeof tl.fitText !== 'boolean')
		errs.push(`fitText phải là boolean (${String(tl.fitText)})`);
	if (tl.roughness !== undefined && !(typeof tl.roughness === 'number' && tl.roughness >= 0))
		errs.push(`roughness phải là số ≥ 0 (${String(tl.roughness)})`);
	if (tl.bowing !== undefined && !(typeof tl.bowing === 'number' && Number.isFinite(tl.bowing)))
		errs.push(`bowing phải là số (${String(tl.bowing)})`);
	const ids = new Set<string>();
	(tl.scenes ?? []).forEach((s, si) => {
		const where = `scenes[${si}](${s.id})`;
		if (!s.id) errs.push(`${where}: thiếu id`);
		if (typeof s.start !== 'number' || typeof s.end !== 'number') errs.push(`${where}: thiếu start/end`);
		if (s.transitionIn && !TRANSITIONS.includes(s.transitionIn.type))
			errs.push(`${where}: transitionIn.type không hợp lệ (${s.transitionIn.type})`);
		if (s.transitionIn?.type === 'zoom-from' && si > 0) {
			const prev = tl.scenes[si - 1];
			if (s.transitionIn.fromElement && !prev.elements.some((e) => e.id === s.transitionIn!.fromElement))
				errs.push(`${where}: fromElement "${s.transitionIn.fromElement}" không có ở scene trước`);
		}
		(s.elements ?? []).forEach((e: TimelineElement, ei) => {
			const w = `${where}.elements[${ei}](${e.id})`;
			if (!e.id) errs.push(`${w}: thiếu id`);
			else if (ids.has(e.id)) errs.push(`${w}: id trùng "${e.id}"`);
			ids.add(e.id);
			if (!ELEMENT_TYPES.includes(e.type)) {
				errs.push(`${w}: type không hợp lệ (${(e as {type: string}).type})`);
				return;
			}
			for (const k of REQUIRED[e.type]) {
				if ((e as unknown as Record<string, unknown>)[k] === undefined) errs.push(`${w}: thiếu "${k}"`);
			}
			if (e.enter && !ENTERS.includes(e.enter)) errs.push(`${w}: enter không hợp lệ (${e.enter})`);
			if (e.exit && !EXITS.includes(e.exit)) errs.push(`${w}: exit không hợp lệ (${e.exit})`);
			if (e.type === 'bar' && e.horizontal !== undefined && typeof e.horizontal !== 'boolean')
				errs.push(`${w}: horizontal phải là boolean (${String(e.horizontal)})`);
			const ex = e as unknown as Record<string, unknown>;
			for (const k of ['rough', 'fit']) {
				if (ex[k] !== undefined && typeof ex[k] !== 'boolean') errs.push(`${w}: ${k} phải là boolean (${String(ex[k])})`);
			}
			if (ex.maxLines !== undefined && !(Number.isInteger(ex.maxLines) && (ex.maxLines as number) >= 1))
				errs.push(`${w}: maxLines phải là số nguyên ≥ 1 (${String(ex.maxLines)})`);
			if (e.type === 'text' && ex.mark !== undefined && !['khoanh', 'gach_chan'].includes(ex.mark as string))
				errs.push(`${w}: mark phải là "khoanh" hoặc "gach_chan" (${String(ex.mark)})`);
		});
	});
	return errs;
};
