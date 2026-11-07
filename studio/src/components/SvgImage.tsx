import React, {useEffect, useRef, useState} from 'react';
import {continueRender, delayRender} from 'remotion';

/**
 * <image> trong SVG (dùng cho mask vẽ nguệch ngoạc). Giữ delayRender tới khi
 * ảnh tải xong để frame render không bị trống.
 */
export const SvgImage: React.FC<
	React.SVGProps<SVGImageElement> & {href: string}
> = ({href, ...rest}) => {
	const [handle] = useState(() =>
		delayRender(`svg-image ${href}`, {timeoutInMilliseconds: 60000}),
	);
	const done = useRef(false);
	const finish = () => {
		if (!done.current) {
			done.current = true;
			continueRender(handle);
		}
	};
	useEffect(() => finish, []); // eslint-disable-line react-hooks/exhaustive-deps
	return <image href={href} onLoad={finish} onError={finish} {...rest} />;
};
