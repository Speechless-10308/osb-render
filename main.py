from src.config import Config
from src.jobs import RenderJob
from tqdm import tqdm

import argparse
import numpy as np
from typing import Optional


class ProgressBar:
    def __init__(self):
        self.pbar: Optional[tqdm] = None

    def __call__(self, current: int, total: int):
        if self.pbar is None:
            self.pbar = tqdm(
                total=total, unit="frames", desc="Rendering", dynamic_ncols=True
            )
        self.pbar.update(current - self.pbar.n)

        if current >= total:
            self.close()

    def close(self):
        if self.pbar is not None:
            self.pbar.close()


def main():
    parser = argparse.ArgumentParser(description="Render osu! storyboards to video.")
    parser.add_argument("osu_file", type=str, help="Path to the .osu file.")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.yaml",
        help="Path to the configuration YAML file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Path to the output video file. Overrides config if set.",
    )
    parser.add_argument(
        "--width", type=int, help="Output video width. Overrides config if set."
    )

    parser.add_argument(
        "--height", type=int, help="Output video height. Overrides config if set."
    )
    parser.add_argument(
        "--fps", type=int, help="Output video FPS. Overrides config if set."
    )
    parser.add_argument(
        "--gpu", action="store_true", help="Use GPU acceleration for rendering."
    )
    args = parser.parse_args()

    config = Config.from_yaml(args.config)

    if args.osu_file:
        config.path.osu_path = args.osu_file
    if args.output:
        config.path.output_path = args.output
    if args.width:
        config.renderer.width = args.width
    if args.height:
        config.renderer.height = args.height
    if args.fps:
        config.renderer.fps = args.fps
    if args.gpu:
        config.renderer.use_gpu = True
    else:
        config.renderer.use_gpu = False

    job = RenderJob(config)

    pbar = ProgressBar()
    job.set_callbacks(progress_callback=pbar)

    try:
        job.start()
    except KeyboardInterrupt:
        job.stop()
    finally:
        pbar.close()


if __name__ == "__main__":
    main()
