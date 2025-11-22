import os
from src.models import Storyboard, Sprite, Layer, Origin, Command, LoopCommand, Vector2
from src.state_engine import StateEngine
from src.parser import StoryboardParser
from src.render import StoryboardRenderer
from src.managers import AssetLoader
import time


def test_render_frame():
    filepath = "C:\\MyOtherFiles\\osu!\\Songs\\1850986 Aoi - King Atlantis\\Aoi - King Atlantis (ScubDomino).osb"

    parser = StoryboardParser()
    storyboard = parser.parse(filepath)
    engine = StateEngine(storyboard)

    assets_loader = AssetLoader(
        "C:\\MyOtherFiles\\osu!\\Songs\\1850986 Aoi - King Atlantis"
    )
    st = time.time()
    render = StoryboardRenderer(engine, assets_loader, width=1920, height=1080, fps=60)

    img = render.render_frame(67465)
    img.save("test_render_frame_output.png")
    print(f"Render time: {time.time() - st} seconds")


if __name__ == "__main__":
    test_render_frame()
