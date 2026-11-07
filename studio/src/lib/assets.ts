import {staticFile} from 'remotion';

/**
 * Quy tắc đường dẫn trong timeline:
 *  - bắt đầu bằng "common/" hoặc "/"  → tính từ thư mục public/ gốc
 *  - http(s):// hoặc data:            → dùng nguyên
 *  - còn lại                           → tính từ public/<videoId>/
 */
export const resolveAsset = (videoId: string, src: string): string => {
	if (/^(https?:|data:|blob:)/.test(src)) return src;
	if (src.startsWith('/')) return staticFile(src.slice(1));
	if (src.startsWith('common/')) return staticFile(src);
	return staticFile(`${videoId}/${src}`);
};
