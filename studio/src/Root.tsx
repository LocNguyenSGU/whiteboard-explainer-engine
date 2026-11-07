import React from 'react';
import {Composition} from 'remotion';
import {TimelineVideo} from './components/TimelineVideo';
import {ThumbChung} from './ThumbChung';
import {calculateTimelineMetadata} from './lib/metadata';

// videoId mặc định; render video khác bằng --props='{"videoId":"...","timelineFile":"timeline-C.json"}'
export const DEFAULT_VIDEO_ID = 'demo-terminal-bench';

export const RemotionRoot: React.FC = () => (
	<>
		<Composition
			id="C"
			component={TimelineVideo}
			durationInFrames={150}
			fps={30}
			width={1920}
			height={1080}
			defaultProps={{videoId: DEFAULT_VIDEO_ID, timelineFile: 'timeline-C.json'}}
			calculateMetadata={calculateTimelineMetadata}
		/>
		<Composition id="Thumb" component={ThumbChung} durationInFrames={1} fps={30} width={1280} height={720}
			defaultProps={{tren: 'Đi Làm IT', lon: ['Tiêu đề', '*nhấn*'], mau: 'cam'}} />
	</>
);
