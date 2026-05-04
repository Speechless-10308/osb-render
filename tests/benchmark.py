"""
Benchmark: render a set of beatmaps end-to-end and report timing stats.

Usage:
    uv run tests/benchmark.py [--width 1920] [--height 1080] [--fps 60] [--gpu]

Output: a Markdown table is printed to stdout and also saved to
``bench_results.md`` so you can copy it into README.
"""
import os
import sys
import time
import re
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser import StoryboardParser
from src.state_engine import StateEngine
from src.render_skia import SkiaRenderer, SkiaRendererGpu
from src.managers import AssetLoader
from src.video import VideoSource


# ---------------------------------------------------------------------------
# Beatmap list — edit this to add / remove entries
# ---------------------------------------------------------------------------
BEATMAPS = [
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_osb_path(osu_path: str) -> str:
    base = os.path.dirname(osu_path)
    filename = os.path.splitext(os.path.basename(osu_path))[0]
    filename = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]\s*$", "", filename)
    return os.path.join(base, filename + ".osb")


def _proj_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ffmpeg_path() -> str:
    name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    return os.path.join(_proj_root(), name)


def _beatmap_name(osu_path: str) -> str:
    """Return a human-readable beatmap identifier."""
    parts = osu_path.replace("\\", "/").split("/")
    folder = parts[-2] if len(parts) >= 2 else ""
    # Remove leading numeric ID
    folder = re.sub(r"^\d+\s+", "", folder)
    # Replace underscores that are surrounded by spaces (osu! naming convention)
    folder = re.sub(r"\s_|_\s", " ", folder)
    folder = re.sub(r"\s+", " ", folder).strip()
    file = os.path.splitext(parts[-1])[0]
    diff_match = re.search(r"\[([^\]]+)\]$", file)
    diff = diff_match.group(1) if diff_match else file
    return f"{folder} [{diff}]"


def _parse_and_build(osu_path: str):
    """Parse .osu + .osb, merge, build engine, return (storyboard, engine, basepath)."""
    basepath = os.path.dirname(osu_path)

    parser = StoryboardParser()
    storyboard = parser.parse(osu_path)

    osb_path = _get_osb_path(osu_path)
    if os.path.exists(osb_path):
        osb_parser = StoryboardParser()
        storyboard.merge(osb_parser.parse(osb_path))

    engine = StateEngine(storyboard)
    return storyboard, engine, basepath


def _duration_ms(storyboard) -> int:
    """Total storyboard duration including video."""
    max_t = 0
    for layer in [
        storyboard.background_layer,
        storyboard.fail_layer,
        storyboard.pass_layer,
        storyboard.foreground_layer,
        storyboard.overlay_layer,
    ]:
        for obj in layer:
            if obj.life_end > max_t:
                max_t = obj.life_end
    return int(max_t)


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def run_benchmark(width: int, height: int, fps: int, gpu: bool, *, out_file: str = "bench_results.md"):
    results = []

    for osu_path in BEATMAPS:
        if not os.path.isfile(osu_path):
            print(f"[SKIP] Not found: {osu_path}")
            continue

        name = _beatmap_name(osu_path)
        print(f"\n{'='*70}")
        print(f"  {name}")
        print(f"{'='*70}")

        # ---- Parse ----
        t0 = time.perf_counter()
        storyboard, engine, basepath = _parse_and_build(osu_path)
        t1 = time.perf_counter()
        parse_ms = (t1 - t0) * 1000

        duration = _duration_ms(storyboard)
        total_frames = (duration * fps) // 1000 + 1
        dur_min = duration // 60000
        dur_sec = (duration % 60000) // 1000

        print(f"  Duration  : {duration} ms  ({dur_min}:{dur_sec:02d})")
        print(f"  Frames    : {total_frames}  (@ {fps} fps)")
        print(f"  Sprites   : {sum(len(getattr(storyboard, l, [])) for l in ['background_layer','fail_layer','pass_layer','foreground_layer','overlay_layer'])}")
        print(f"  Video     : {'yes' if storyboard.video else 'no'}")
        print(f"  Parse    : {parse_ms:.0f} ms")

        # ---- Video source ----
        video_source = None
        if storyboard.video is not None:
            video_path = os.path.join(basepath, storyboard.video.filepath)
            video_source = VideoSource(video_path, ffmpeg_path=_ffmpeg_path())

        # ---- Render ----
        asset_loader = AssetLoader(base_path=basepath)
        cls = SkiaRendererGpu if gpu else SkiaRenderer
        renderer = cls(
            engine, asset_loader,
            width=width, height=height,
            video_source=video_source,
            video_object=storyboard.video,
        )

        print(f"  Rendering...")
        t2 = time.perf_counter()

        for i in range(total_frames):
            time_ms = int(i * 1000 / fps)
            renderer.render_frame(time_ms)

            if (i + 1) % max(1, total_frames // 10) == 0:
                pct = (i + 1) * 100 // total_frames
                print(f"    {pct}%  ({i+1}/{total_frames})", flush=True)

        t3 = time.perf_counter()
        render_ms = (t3 - t2) * 1000
        total_ms = (t3 - t0) * 1000

        avg_fps = total_frames / (render_ms / 1000) if render_ms > 0 else 0

        print(f"  Render    : {render_ms/1000:.1f} s  ({avg_fps:.0f} fps avg)")
        print(f"  Total     : {total_ms/1000:.1f} s")

        renderer.close()
        if video_source:
            video_source.close()

        results.append({
            "name": name,
            "duration": f"{int(dur_min)}:{dur_sec:02d}",
            "resolution": f"{width}x{height}",
            "fps": str(fps),
            "render_time": f"{render_ms/1000:.1f} s",
            "avg_fps": f"{avg_fps:.0f}",
        })

    # ---- Markdown table ----
    lines = []
    lines.append("| Beatmap | Duration | Resolution | FPS | Render Time |")
    lines.append("| :-- | :-- | :-- | :-- | :-- |")
    for r in results:
        lines.append(
            f"| {r['name']} | {r['duration']} | {r['resolution']} | "
            f"{r['fps']} | {r['render_time']} |"
        )

    table = "\n".join(lines)
    print(f"\n{'='*70}")
    print("  Benchmark Results (Markdown)")
    print(f"{'='*70}\n")
    print(table)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(table + "\n")
    print(f"\nSaved to: {out_file}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Benchmark storyboard rendering")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--out", default="bench_results.md")
    args = ap.parse_args()

    run_benchmark(args.width, args.height, args.fps, args.gpu, out_file=args.out)
