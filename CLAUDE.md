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

# Run tests
uv run tests/test_engine.py    # StateEngine: construction, parser integration, real storyboard
uv run tests/test_canvas.py    # Renderer: frame rendering via PIL, Skia CPU, Skia GPU

# Build with Nuitka
uv run nuitka app.py --standalone --enable-plugin=pyside6 --windows-console-mode=disable

Python 3.13 via uv. No test framework installed -- tests are standalone scripts run directly (no pytest).

## Architecture

This app renders osu! storyboard (.osb) files into video. The rendering pipeline: **.osb file → Parser → Storyboard model → StateEngine → Renderer → raw frames → ffmpeg → .mp4**.

### Core pipeline (`src/`)

- **[src/config.py](src/config.py)** — Pydantic `Config` model holding app/path/renderer settings, loaded from `configs/config.yaml`
- **[src/parser.py](src/parser.py)** — `StoryboardParser` reads .osb files and builds a `Storyboard` model. Handles Sprite/Animation objects, all command types (F/M/MX/MY/S/V/R/C/P), Loop and Trigger commands, shorthand expansion
- **[src/models.py](src/models.py)** — Dataclass models: `Storyboard` (5 layers), `SBObject`/`Sprite`/`Animation`, `Command`/`LoopCommand`, `ObjectState`, `Vector2`, enums (`Layer`, `Origin`, `LoopType`)
- **[src/state_engine.py](src/state_engine.py)** — `StateEngine` computes the interpolated `ObjectState` for any object at a given time. Handles easing, looping, parameter commands (flip/additive), animation frames, command category deduplication (e.g. MX/MY override M's x/y)
- **[src/easings.py](src/easings.py)** — All 34 osu! easing functions (linear, quad, cubic, quart, quint, sine, expo, circ, elastic, back, bounce) with `apply_easing(id, t)` dispatcher
- **[src/render_skia.py](src/render_skia.py)** — Two Skia renderers: `SkiaRenderer` (CPU, uses `SkSurface.MakeRaster`) and `SkiaRendererGpu` (GPU, uses GLFW + Skia GrDirectContext). Both draw objects layer-by-layer with transforms (translate/rotate/scale/flip), opacity, additive blending, and color tinting. Uses time-bucketed preprocessing to skip objects not active at a given time.
- **[src/managers.py](src/managers.py)** — `AssetLoader` caches loaded images by path, returns a transparent 1x1 placeholder for missing assets
- **[src/jobs.py](src/jobs.py)** — `RenderJob` orchestrates the full render: parses storyboard, creates ffmpeg subprocess, feeds raw frames via stdin pipe. CPU path uses `multiprocessing.Pool` with worker processes; GPU path renders frames sequentially. After rendering, merges audio from the beatmap via ffmpeg.

### GUI (`apps/`)

- **[apps/main_window.py](apps/main_window.py)** — PySide6 `QMainWindow` with file selection, resolution/FPS/GPU controls, progress bar, log view
- **[apps/threads.py](apps/threads.py)** — `RenderThread` (QThread) runs `RenderJob` in background, bridges progress/log signals to GUI
- **[apps/widgets.py](apps/widgets.py)** — `ResolutionWidget` with aspect-ratio-locked width/height spinboxes
- **[apps/dialogs.py](apps/dialogs.py)** — `AdvancedSettingsDialog` for encoder preset, CRF, sampling method, audio toggle

### Config

- **[configs/config.yaml](configs/config.yaml)** — Default configuration with `app` (last directory), `path` (osu/output paths), and `renderer` (resolution, FPS, GPU toggle, encoder preset, CRF, audio toggle, sample method) sections. CLI arguments override YAML values via `Config.from_yaml()`.

### Entry points

- **[main.py](main.py)** — CLI with argparse, creates `Config` from YAML + CLI overrides, runs `RenderJob` with tqdm progress bar
- **[app.py](app.py)** — PySide6 QApplication bootstrap, creates `MainWindow`
- **[pyproject.toml](pyproject.toml)** — Project metadata, depends on glfw, loguru, nuitka, pydantic, pyside6, pyyaml, skia-python, tqdm. Python >=3.13.

### Other

- **[reference/](reference/)** — osu! storyboard specification reference docs for general rules, objects, commands, audio, compound commands, and shorthand syntax
- **ffmpeg.exe** — Bundled ffmpeg binary for video encoding and audio merging
- **Nuitka builds** — `app.build/` and `app.dist/` are Nuitka-compiled outputs of `app.py`

## Key design notes

- The renderer uses a **time-bucketing optimization**: objects are pre-bucketed into 1-second intervals so each frame only iterates active objects
- osu! uses a 640x480 coordinate system; the renderer scales to output resolution using `height / 480.0` as the scale factor, centering horizontally with an x-offset
- Command shorthand expansion happens in the parser: multiple value pairs with equal duration are expanded into sequential commands; start-only shorthand duplicates values for end
- GPU renderer creates an invisible GLFW window for OpenGL context, renders via Skia GPU backend
- Audio merge runs as a second pass after raw video rendering, combining the output with the beatmap's audio file (auto-detected alongside .osb from the .osu file path)
- The CLI accepts an `.osu` file path; the program automatically locates the adjacent `.osb` storyboard and audio file
