import os
from src.models import Storyboard, Sprite, Layer, Origin, Command, LoopCommand, Vector2
from src.state_engine import StateEngine
from src.parser import StoryboardParser
from src.render import StoryboardRenderer
from src.render_skia import SkiaRenderer
from src.managers import AssetLoader
import time


def test_render_frame_pil(times, filepath):
    basepath = os.path.dirname(filepath)

    parser = StoryboardParser()
    storyboard = parser.parse(filepath)
    engine = StateEngine(storyboard)

    assets_loader = AssetLoader(
        base_path=basepath,
    )

    render = StoryboardRenderer(engine, assets_loader, width=1920, height=1080)
    st = time.time()
    img = render.render_frame(times)
    et = time.time()
    print(f"Render time (PIL) for {times} ms: {(et - st)*1000:.2f} ms")
    img.save("test_render_frame_output_pil.png")


def test_render_frame_skia(times, filepath):
    basepath = os.path.dirname(filepath)

    parser = StoryboardParser()
    storyboard = parser.parse(filepath)
    engine = StateEngine(storyboard)

    assets_loader = AssetLoader(
        base_path=basepath,
    )

    render = SkiaRenderer(engine, assets_loader, width=1920, height=1080)
    st = time.time()
    img = render.render_frame(times)
    et = time.time()
    print(f"Render time (Skia) for {times} ms: {(et - st)*1000:.2f} ms")
    img.save("test_render_frame_output_skia.png")


if __name__ == "__main__":
    times = 154363
    filepath = "C:\\MyOtherFiles\\osu!\\Songs\\2412263 nm-y - Datura Sh__va\\nm-y - Datura Shva (iljaaz).osb"
    test_render_frame_pil(
        times,
        filepath,
    )

    test_render_frame_skia(
        times,
        filepath,
    )
