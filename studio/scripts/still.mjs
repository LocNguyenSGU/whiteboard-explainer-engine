#!/usr/bin/env node
// npm run still -- <compId> <frame> <out.png> [các cờ remotion khác]
import {spawnSync} from 'node:child_process';

const [comp, frame, out, ...rest] = process.argv.slice(2);
if (!comp || frame === undefined || !out) {
	console.error('Cách dùng: npm run still -- <compId> <frame> <out.png> [--props=...]');
	process.exit(1);
}
const r = spawnSync('npx', ['remotion', 'still', 'src/index.ts', comp, out, `--frame=${frame}`, ...rest], {stdio: 'inherit'});
process.exit(r.status ?? 1);
