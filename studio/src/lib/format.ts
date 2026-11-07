/**
 * Định dạng số kiểu Việt Nam: phân cách nghìn bằng "." và thập phân bằng ",".
 * Tự làm thủ công (không dùng Intl) để kết quả xác định trên mọi máy render.
 */
export const formatVi = (
	value: number,
	decimals = 0,
	thousands = true,
): string => {
	const neg = value < 0;
	const fixed = Math.abs(value).toFixed(Math.max(0, decimals));
	const [intPart, decPart] = fixed.split('.');
	const grouped = thousands
		? intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
		: intPart;
	const out = decPart ? `${grouped},${decPart}` : grouped;
	return neg && Number(fixed) !== 0 ? `−${out}` : out;
};
