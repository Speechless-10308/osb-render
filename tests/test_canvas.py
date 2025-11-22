import os
from src.models import Storyboard, Sprite, Layer, Origin, Command, LoopCommand, Vector2
from src.state_engine import StateEngine
from src.parser import StoryboardParser
from src.render import StoryboardRenderer
from src.render_cv import RendererCV
from src.managers import AssetLoader
import time
import cv2


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
    print(f"Render time: {time.time() - st} seconds")
    img.save("test_render_frame_output_pil.png")


if __name__ == "__main__":
    test_render_frame_pil(
        5193,
        "C:\\MyOtherFiles\\osu!\\Songs\\1054045 a_hisa - Alexithymia _ Lupinus _ Tokei no Heya to Seishin Sekai\\a_hisa - Alexithymia  Lupinus  Tokei no Heya to Seishin Sekai (ProfessionalBox).osb",
    )
