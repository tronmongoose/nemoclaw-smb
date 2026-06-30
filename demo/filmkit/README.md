# filmkit — narrated demo film maker

> **Canonical tool:** the config-driven `demo-film` user-level skill
> (`~/.claude/skills/demo-film/`). The film is now declared in **`demo/film.json`** and
> rebuilt with:
> `bash ~/.claude/skills/demo-film/scripts/run.sh demo/film.json demo/nemoclaw-pm-narrated.mp4`
> (run from the repo root, with the API on :8010 and the UI on :5174). The scripts below are
> the original hardcoded version, kept as a worked reference.

Turns the running STR web app into a short narrated, captioned MP4. Used to produce
`demo/nemoclaw-pm-narrated.mp4`. Fully local: no OpenAI, no cloud TTS, no browser download.

**Pipeline:** populate the app with real data → Playwright captures one annotated
screenshot per scene → Kokoro narrates each line → ffmpeg stitches static slides
(each as long as its narration) with baked-in caption bars + HTML title/end cards.

## Prereqs (macOS)
- Google Chrome installed (Playwright drives it via `channel: "chrome"` — no download).
- `ffmpeg` (`brew install ffmpeg`). Note: this build has **no `drawtext`** (no freetype),
  which is why title/end cards are rendered as HTML screenshots, not text overlays.
- `uv`, `node`.

## One-time setup (scratch dir defaults to /tmp/nemo-film)
```
WORK=/tmp/nemo-film; mkdir -p $WORK/scenes $WORK/aud; cd $WORK
npm init -y && npm i playwright-core           # capture
uv venv pv --python 3.12                        # TTS env
uv pip install --python pv/bin/python kokoro-onnx soundfile
# Kokoro model (~325MB) + voices — from the thewh1teagle/kokoro-onnx release:
curl -sL -o kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -sL -o voices-v1.0.bin  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
# copy these scripts into $WORK
cp <repo>/demo/filmkit/* $WORK/
```

## Run order (with the app up: API :8010 DEMO_MODE, UI :5174 → :8010)
```
cd /tmp/nemo-film
bash populate.sh                                  # fill marketplace metrics
pv/bin/python gen_kokoro.py                       # narration -> aud/s*.wav (voice af_heart)
pv/bin/python make-cards.js  || node make-cards.js  # title.png + end.png (HTML screenshots)
FILM_BASE=http://localhost:5174 node narrate.js   # scenes/*.png with caption bars
FILM_OUT=<repo>/demo/nemoclaw-pm-narrated.mp4 bash assemble.sh
```
`make-cards.js` and `narrate.js` are Node (run with `node`). Keep the scene list in
`narrate.js`, the narration list in `gen_kokoro.py`, and the slide order in
`assemble.sh` in sync (title, <scenes…>, end).

## Gotchas (learned the hard way)
- **Run shell scripts with `bash`**, not the default zsh — zsh arrays are 1-indexed and
  silently misalign audio↔image.
- **Populate before capture** or panels show "No data". Some results are local component
  state — the capture must click those buttons (Swarm: marketing/sales/pricing).
- The entity graph (react-force-graph) only frames well if its `graphData` is memoized
  (else the sim resets mid-render) and the box height is tuned; `zoomToFit` is flaky headless.
- Voice: Kokoro `af_heart` is the one that reads naturally. Piper/`say` were too stiff.
