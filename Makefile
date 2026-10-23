# ─────────────────────────────────────────────────────────────────────────────
# DeepSeek V4.1-Flash · 1017 — motion graphics system
#   make            list targets
#   make all        analysis → timeline → docs → ass → web data
#   make verify     consistency checks across renderer / player / docs
#   make player     serve the live 60fps player on :5173
# ─────────────────────────────────────────────────────────────────────────────
SHELL := /bin/bash
SRC    ?= Deepseek strikes again.mp4
PY     ?= python3
SEGS   ?= 0-62,150-240,676-762,1244-1300,1395-1500,1500-1585

.PHONY: help all analyze timeline docs ass verify player build webdata \
        render-highlights render-intro audio preview clean

help:
	@echo "make all               analyse source → timeline → docs → ass → web data"
	@echo "make analyze           re-run the measurement pass (~70 s)"
	@echo "make timeline          rebuild graphics/timeline.json from annotation"
	@echo "make docs              regenerate docs/*.md from the data"
	@echo "make ass               regenerate render/overlay.ass + scripts/ffmpeg_overlay.sh"
	@echo "make verify            schema / coverage / collision / artefact checks"
	@echo "make player            npm install + vite dev on 0.0.0.0:5173"
	@echo "make render-highlights 60fps burn-in of the key windows → render/"
	@echo "make render-intro      48 s · 1080p60 new film → render/"
	@echo "make audio             original 120 BPM score"
	@echo "make preview           30 s proof-of-concept burn-in"
	@echo "make clean             drop generated media (keeps sources + analysis json)"

all: analyze timeline docs ass verify

analyze:
	$(PY) scripts/analyze_video.py --video "$(SRC)"

timeline:
	$(PY) scripts/build_timeline.py

docs: 
	$(PY) scripts/make_docs.py

ass:
	$(PY) scripts/make_ffmpeg_ass.py

verify:
	$(PY) scripts/verify.py --build

player: webdata
	cd web && npm install --no-audit --no-fund && npm run dev

webdata:
	@mkdir -p web/src/data && $(PY) scripts/build_timeline.py >/dev/null

build:
	cd web && npm install --no-audit --no-fund && npx tsc -b && npx vite build

render-highlights:
	$(PY) scripts/render_overlay.py --segments "$(SEGS)" --render-fps 60 \
		--crf 21 --preset veryfast --out render/deepseek_overlay_highlights.mp4

render-intro: audio
	$(PY) scripts/render_intro.py --out render/intro_1017.mp4 --crf 19

audio:
	$(PY) scripts/synth_audio.py --dur 48 --out render/intro_bed.wav

preview:
	$(PY) scripts/render_overlay.py --range 0-30 --out out/preview_0_30.mp4

clean:
	rm -f render/*.mp4 render/*.wav render/*.m4a out/*.mp4
