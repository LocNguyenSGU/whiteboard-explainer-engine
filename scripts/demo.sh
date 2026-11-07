#!/usr/bin/env bash
# Build the demo: storyboard YAML + narration timing -> timeline JSON -> MP4 (Remotion).
#   scripts/demo.sh            build timeline and render out/demo.mp4
#   scripts/demo.sh --check    only run the storyboard checks (timing gaps, overlaps, numbers), no render
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ID=demo-terminal-bench
EX="$ROOT/examples/terminal-bench"
PUB="$ROOT/studio/public/$ID"
PY="${PYTHON:-python3}"

mkdir -p "$PUB/assets" "$ROOT/out"
cp "$EX"/assets/* "$PUB/assets/"
cp "$EX/voice/voice.wav" "$PUB/voice.wav"

if [[ "${1:-}" == "--check" ]]; then
  "$PY" "$ROOT/engine/khuon/dung.py" "$EX/storyboard.yaml" "$EX/voice" "$PUB" --kiem-tra
  exit 0
fi
"$PY" "$ROOT/engine/khuon/dung.py" "$EX/storyboard.yaml" "$EX/voice" "$PUB"
cd "$ROOT/studio"
npx remotion render src/index.ts C "$ROOT/out/demo.mp4" --timeout=120000 --props="{\"videoId\":\"$ID\",\"timelineFile\":\"timeline-C.json\"}"
echo "→ out/demo.mp4"
