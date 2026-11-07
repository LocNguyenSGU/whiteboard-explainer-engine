import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, Img, staticFile} from 'remotion';
import {FONT_SANS, loadFonts} from './fonts';

// Thumbnail 1280×720 DÙNG CHUNG cho mọi video (25/10/2026): chữ bên trái, ảnh minh hoạ bên phải, nội dung lấy từ props.
// Không viết composition riêng cho từng video nữa. Render qua pipeline/lam_thumbnail.py.
const INK = '#1D2433';
const INK2 = '#5B6474';
const MAU: Record<string, string> = {cam: '#F2611D', do: '#E03E3E', xanh: '#2F6FEB', 'xanh-la': '#1F9D55', den: INK};

export type ThumbChungProps = {
	/** dòng nhỏ phía trên (tên series), vd. "Tuần IT có gì hot #2" */
	tren?: string;
	/** các dòng chữ lớn; "*chữ*" = tô màu nhấn */
	lon: string[];
	/** viên chữ nổi bật dưới dòng lớn (con số), vd. "+19% tiền" */
	vien?: string;
	/** dòng phụ dưới cùng */
	duoi?: string;
	mau?: string;
	/** đường dẫn ảnh trong studio/public, vd. "2026-10-tuan-it-hot-02/assets/sketch-x.png" */
	anh?: string;
};

const useFonts = () => {
	const [handle] = useState(() => delayRender('fonts'));
	useEffect(() => {
		loadFonts().then(() => continueRender(handle)).catch((e) => cancelRender(e));
	}, [handle]);
};

export const ThumbChung: React.FC<ThumbChungProps> = ({tren, lon, vien, duoi, mau = 'cam', anh}) => {
	useFonts();
	const nhan = MAU[mau] ?? mau;
	// lineHeight 1.2: dấu tiếng Việt (Ắ, Ẻ, Ổ) không chạm dòng trên (Lộc góp ý 25/10/2026)
	const co = lon.length >= 3 ? 96 : 116;
	return (
		<AbsoluteFill style={{background: 'radial-gradient(circle at 78% 45%, #FFF0E8 0%, #FCFCFA 60%)', fontFamily: FONT_SANS, overflow: 'hidden'}}>
			{anh ? <Img src={staticFile(anh)} style={{position: 'absolute', right: -10, top: 110, width: 640, objectFit: 'contain'}} /> : null}
			<div style={{position: 'absolute', left: 60, top: 40, width: 780}}>
				{tren ? <div style={{fontSize: 38, fontWeight: 700, color: INK2, marginBottom: 20}}>{tren}</div> : null}
				{lon.map((d, i) => (
					<div key={i} style={{fontSize: co, fontWeight: 800, lineHeight: 1.2, letterSpacing: 0, whiteSpace: 'nowrap', color: INK}}>
						{d.split(/(\*[^*]+\*)/).map((p, k) =>
							p.startsWith('*') ? <span key={k} style={{color: nhan}}>{p.slice(1, -1)}</span> : <span key={k}>{p}</span>,
						)}
					</div>
				))}
				{vien ? (
					<div style={{display: 'inline-block', marginTop: 20, background: nhan, color: '#FFFFFF', fontSize: 64, fontWeight: 800,
						padding: '4px 22px 12px', borderRadius: 16}}>{vien}</div>
				) : null}
			</div>
			{duoi ? <div style={{position: 'absolute', left: 64, bottom: 50, fontSize: 38, fontWeight: 700, color: INK2}}>{duoi}</div> : null}
		</AbsoluteFill>
	);
};
