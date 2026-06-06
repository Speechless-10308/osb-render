# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```shell
# Install dependencies
uv sync

# Run CLI (CPU rendering)
uv run main.py [osu_path] -o [output_path] --width 1920 --height 1080

# Run CLI (GPU acceleration)
uv run main.py [osu_path] -o [output_path] --width 1920 --height 1080 --gpu

# Run GUI
uv run app.py

# Run tests (pytest)
uv run pytest tests/ -v

# Run demo/debug scripts (standalone, non-pytest)
uv run scripts/engine_demo.py         # StateEngine: construction, parser integration, real storyboard
uv run scripts/canvas_demo.py         # Renderer: frame rendering via PIL, Skia CPU, Skia GPU
uv run scripts/debug_frame_demo.py    # Single-frame debug render with sprite labels + render time overlay

# Benchmark
uv run tests/benchmark.py                              # CPU, 1920x1080 @ 60 fps
uv run tests/benchmark.py --gpu --width 1280 --height 720 --fps 30

# Build with Nuitka
uv run nuitka app.py --standalone --enable-plugin=pyside6 --windows-console-mode=disable --include-data-dir=icons=icons --include-data-dir=themes=themes
```

Python 3.13 via uv. Tests use pytest; demo scripts live in `scripts/`.

## Architecture

This app renders osu! storyboard files into video. The rendering pipeline: **.osu / .osb files → Parser → Storyboard model → StateEngine → Renderer → raw frames → ffmpeg → .mp4**.

### Core pipeline (`src/`)

- **[src/config.py](src/config.py)** — Pydantic `Config` model holding app/path/renderer settings, loaded from `configs/config.yaml`
- **[src/parser.py](src/parser.py)** — `StoryboardParser` reads both `.osu` and `.osb` files and builds a `Storyboard` model. Handles Sprite/Animation/Video objects, all command types (F/M/MX/MY/S/V/R/C/P), Loop and Trigger commands, shorthand expansion. Video events (`Video,start_time,"file",x,y` or `1,...`) are parsed into a `VideoObject` stored on `Storyboard.video`. Background/image lines (`0,0,"bg.jpg",0,0`) are silently skipped.
- **[src/models.py](src/models.py)** — Dataclass models: `Storyboard` (5 layers + optional `VideoObject`), `SBObject`/`Sprite`/`Animation`, `VideoObject` (filepath, start_time, x/y offset), `Command`/`LoopCommand`, `ObjectState`, `Vector2`, enums (`Layer`, `Origin`, `LoopType`). `Storyboard.merge()` appends another storyboard's objects to each layer (used for .osu + .osb combining); `Storyboard.is_empty()` checks for renderable content.
- **[src/state_engine.py](src/state_engine.py)** — `StateEngine` computes the interpolated `ObjectState` for any object at a given time. Handles easing, looping, parameter commands (flip/additive), animation frames, command category deduplication (e.g. MX/MY override M's x/y)
- **[src/easings.py](src/easings.py)** — All 34 osu! easing functions (linear, quad, cubic, quart, quint, sine, expo, circ, elastic, back, bounce) with `apply_easing(id, t)` dispatcher
- **[src/render_skia.py](src/render_skia.py)** — Two Skia renderers: `SkiaRenderer` (CPU, uses `SkSurface.MakeRaster`) and `SkiaRendererGpu` (GPU, uses GLFW + Skia GrDirectContext). Both draw objects layer-by-layer with transforms (translate/rotate/scale/flip), opacity, additive blending, and color tinting. Uses time-bucketed preprocessing. Video frames are drawn first on the background layer (object-fit: cover scaling, centered with x/y offset). Both renderers accept `video_source` / `video_object` parameters. `SkiaRendererGpu.close()` destroys the GLFW window and abandons the Skia context but does **not** call `glfw.terminate()` (GLFW stays initialized for subsequent renderers).
- **[src/video.py](src/video.py)** — `VideoSource` decodes video frames via a single persistent ffmpeg pipe. A background thread continuously reads raw RGBA frames from the pipe into a bounded dict buffer (~90 frames, ~333 MB for 720p). The main thread retrieves frames by index via dict lookup (O(1), ~microseconds). Backpressure: the decode thread blocks when the buffer is full; old frames are evicted as the consumer passes them. Timeout-based eviction (0.1 s) handles non-sequential access (e.g. debug mode rendering a frame far from the start). Video plays once and stops rendering after `duration_ms`.
- **[src/managers.py](src/managers.py)** — `AssetLoader` caches loaded images by path, returns a transparent 1x1 placeholder for missing assets
- **[src/jobs.py](src/jobs.py)** — `RenderJob` orchestrates the full render: parses `.osu` first, then merges `.osb` on top, creates `VideoSource` if a video event is present, creates ffmpeg subprocess, feeds raw frames via stdin pipe. CPU path uses `multiprocessing.Pool` with worker processes (each worker gets its own `VideoSource`); GPU path renders frames sequentially. After rendering, merges audio via ffmpeg.

### GUI (`apps/`)

- **[apps/main_window.py](apps/main_window.py)** — `MainWindow` orchestrator: frameless window with drop shadow, custom title bar, animated collapsible sidebar, QStackedWidget pages, render lifecycle, theme switching. Window drag and resize via CustomGrips.
- **[apps/title_bar.py](apps/title_bar.py)** — `TitleBar(QFrame)` — custom title bar with sidebar toggle (hamburger), logo, title, theme toggle button, and window control buttons (minimize/maximize/close). Handles window dragging and double-click maximize.
- **[apps/sidebar.py](apps/sidebar.py)** — `Sidebar(QFrame)` — collapsible left nav (200px ↔ 60px animated). 3 checkable page buttons (Home/Settings/About) in exclusive QButtonGroup. Emits `page_changed(int)` and `toggled(bool)`. QSS property `collapsed` controls icon-only mode.
- **[apps/custom_grips.py](apps/custom_grips.py)** — `CustomGrip(QWidget)` — invisible edge resize handles for frameless window (ported from PyDracula, MIT).
- **[apps/threads.py](apps/threads.py)** — `RenderThread` (QThread) runs `RenderJob` in background, bridges progress/log signals to GUI
- **[apps/widgets.py](apps/widgets.py)** — `ResolutionWidget` with aspect-ratio-locked width/height spinboxes. All objectNames set for QSS targeting; no inline styles.
- **[apps/pages/](apps/pages/)** — Page classes for the stacked widget:
  - `home_page.py` — `HomePage`: 3-card layout (File Source, Parameters grid, Execution Monitor with collapsible console drawer). Console auto-expands on ERROR/WARNING logs.
  - `settings_page.py` — `SettingsPage` with cards: FFmpeg Encoding (preset, CRF, sampling, pixel format, tuning, GOP, B-frames), Audio (codec, bitrate), Configuration (path changer, reset defaults). Auto-saves on any widget change.
  - `about_page.py` — `AboutPage`: logo, version, project description, credits (static content)

### Theming (`themes/`)

- **[themes/osboard_dark.qss](themes/osboard_dark.qss)** — Dark Dracula-based QSS theme. All styling via objectName selectors.
- **[themes/osboard_light.qss](themes/osboard_light.qss)** — Light theme: Background `#F8F9FA`, Cards `#FFFFFF`, Primary `#FF66AA`, Text `#2E354F`, Accent `#9D72FF`.
- Runtime theme switching via title bar button. Preference persisted in `Config.app.theme`.
- Zero inline `setStyleSheet()` calls in Python.

### Tests (`tests/`)

Pytest-based unit tests (220 tests across 7 files):

- **[tests/test_models.py](tests/test_models.py)** — `Vector2` arithmetic, enums, `Command`/`LoopCommand`/`SBObject`/`Sprite`/`Animation`/`ObjectState`/`VideoObject` construction, `Storyboard` layer routing, merge, and emptiness checks
- **[tests/test_easings.py](tests/test_easings.py)** — All 35 easing functions (0–34): boundary values, clamping, known midpoints, in/out monotonicity, in-out symmetry, dispatch table coverage
- **[tests/test_config.py](tests/test_config.py)** — `Config` defaults, `from_yaml()` for valid/partial/missing files, `to_yaml()` round-trip, parent directory creation
- **[tests/test_parser.py](tests/test_parser.py)** — `StoryboardParser`: file errors, comments/blanks, sprite/animation parsing, video events, all command types, shorthand expansion (start-only, multi-segment, insufficient params), loops, triggers (ignored), `[Variables]` substitution, indent handling, error recovery
- **[tests/test_state_engine.py](tests/test_state_engine.py)** — `StateEngine`: lifetime calculation, visibility gating, fade/move/scale/rotation/color interpolation, P commands (flip/additive), loop iteration/wrap-around, command category deduplication, animation frames (loop-forever/loop-once), parser+engine integration
- **[tests/test_managers.py](tests/test_managers.py)** — `AssetLoader`: path normalization, image caching, missing-file/error fallback to 1×1 transparent placeholder
- **[tests/test_video.py](tests/test_video.py)** — `VideoSource`: metadata initialisation, `is_valid` gating, frame index calculation, ffmpeg probe regex parsing, close behaviour

### Demo scripts (`scripts/`)

Standalone scripts for manual testing and visual debugging (run directly, not via pytest):

- **[scripts/engine_demo.py](scripts/engine_demo.py)** — StateEngine manual construction, parser integration, real storyboard rendering
- **[scripts/canvas_demo.py](scripts/canvas_demo.py)** — Single-frame rendering via PIL, Skia CPU, Skia GPU
- **[scripts/debug_frame_demo.py](scripts/debug_frame_demo.py)** — Renders a single frame with debug overlays: sprite filepath labels, frame timestamp, and render time. Supports `--gpu` and custom resolution. Auto-locates companion `.osb` when given a `.osu` file.
- **[tests/benchmark.py](tests/benchmark.py)** — End-to-end benchmark: parses + renders a list of beatmaps, prints a Markdown results table. Add beatmap paths to the `BEATMAPS` list, then run with `--width`, `--height`, `--fps`, `--gpu` flags.

### Config

- **[configs/config.yaml](configs/config.yaml)** — Default configuration with `app` (last directory), `path` (osu/output paths), and `renderer` (resolution, FPS, GPU toggle, encoder preset, CRF, audio toggle, sample method) sections. CLI arguments override YAML values via `Config.from_yaml()`.

### Entry points

- **[main.py](main.py)** — CLI with argparse, creates `Config` from YAML + CLI overrides, runs `RenderJob` with tqdm progress bar
- **[app.py](app.py)** — PySide6 QApplication bootstrap, loads initial QSS theme, creates `MainWindow`
- **[pyproject.toml](pyproject.toml)** — Project metadata, depends on glfw, loguru, nuitka, pydantic, pyside6, pyyaml, skia-python, tqdm. Python >=3.13.

### Other

- **[reference/](reference/)** — osu! specification reference docs: general rules, objects, commands, audio, compound commands, shorthand syntax, and `.osu` file format
- **ffmpeg.exe** — Bundled ffmpeg binary used for video encoding, audio merging, video frame decoding
- **Nuitka builds** — `app.build/` and `app.dist/` are Nuitka-compiled outputs of `app.py`

## Key design notes

- **Frameless window**: Uses `Qt.FramelessWindowHint` + `Qt.WA_TranslucentBackground`. Custom title bar handles dragging and window controls. `QGraphicsDropShadowEffect` on `#bgApp` provides the shadow. `CustomGrip` widgets on all 4 edges handle resizing.
- **.osu + .osb merge order**: `.osu` `[Events]` are parsed first, then `.osb` is merged on top. Within each layer, `.osu` objects come first (rendered behind), `.osb` objects are appended after (rendered on top). Layer hierarchy (Background < Fail < Pass < Foreground < Overlay) is preserved across both files.
- The renderer uses a **time-bucketing optimization**: objects are pre-bucketed into 1-second intervals so each frame only iterates active objects
- osu! uses a 640x480 coordinate system; the renderer scales to output resolution using `height / 480.0` as the scale factor, centering horizontally with an x-offset
- Command shorthand expansion happens in the parser: multiple value pairs with equal duration are expanded into sequential commands; start-only shorthand duplicates values for end
- **Flip origin adjustment**: when `flip_h`/`flip_v` is active, the origin offset is mirrored (`ox = w - ox`, `oy = h - oy`) so the visual bounding box stays anchored to the same side of the origin — only the content is mirrored, not the position
- **Video decoding**: a single ffmpeg pipe + background thread decodes frames ahead of the renderer. `get_frame()` is a dict lookup — effectively free. The pipe is never terminated between beatmaps.
- GPU renderer creates an invisible GLFW window for OpenGL context, renders via Skia GPU backend. `glfw.terminate()` must **never** be called during normal operation — only destroy the window and abandon the Skia context between renderers.
- Audio merge runs as a second pass after raw video rendering, combining the output with the beatmap's audio file (auto-detected alongside .osb from the .osu file path)
- The CLI accepts an `.osu` file path; the program automatically locates the adjacent `.osb` storyboard and audio file
- Video objects play once (from `start_time` to `start_time + duration_ms`), then stop rendering — they do not hold the last frame
