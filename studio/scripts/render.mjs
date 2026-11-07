#!/usr/bin/env node
// npm run render -- <compId> <out.mp4> [các cờ remotion khác, vd --props=... --concurrency=8]
import {spawnSync} from 'node:child_process';

const [comp, out, ...rest] = process.argv.slice(2);
if (!comp || !out) {
	console.error('Cách dùng: npm run render -- <compId> <out.mp4> [--props=...]');
	process.exit(1);
}
const r = spawnSync('npx', ['remotion', 'render', 'src/index.ts', comp, out, ...rest], {stdio: 'inherit'});
process.exit(r.status ?? 1);
