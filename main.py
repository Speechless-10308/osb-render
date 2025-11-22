from src.render_skia import SkiaRenderer, SkiaRendererGpu
from src.state_engine import StateEngine
from src.managers import AssetLoader
from src.models import Storyboard
from src.parser import StoryboardParser
from tqdm import tqdm

import argparse
import os
import subprocess
import multiprocessing
import time
from typing import Optional

worker_renderer: Optional[SkiaRenderer] = None


def init_worker(engine: StateEngine, asset_path: str, width: int, height: int):
    global worker_renderer
    assets_loader = AssetLoader(base_path=asset_path)
    worker_renderer = SkiaRenderer(engine, assets_loader, width=width, height=height)


def render_frame_worker(time_ms: int) -> bytes:
    global worker_renderer
    if worker_renderer is None:
        raise RuntimeError("Worker renderer not initialized")
    return worker_renderer.render_frame(time_ms).tobytes()


def get_video_duration(storyboard: Storyboard) -> int:
    max_time = 0
    layers = [
        storyboard.background_layer,
        storyboard.fail_layer,
        storyboard.pass_layer,
        storyboard.foreground_layer,
        storyboard.overlay_layer,
    ]

    for layer in layers:
        for obj in layer:
            obj_end_time = obj.life_end
            if obj_end_time > max_time:
                max_time = obj_end_time
    return max_time


def main():
    parser = argparse.ArgumentParser(description="Render storyboard to video")
    parser.add_argument("osb_path", type=str, help="Path to the .osb storyboard file")
    parser.add_argument(
        "--output", "-o", help="Output video file", default="output.mp4"
    )
    parser.add_argument("--width", type=int, default=1280, help="Video width")
    parser.add_argument("--height", type=int, default=720, help="Video height")
    parser.add_argument("--fps", type=int, default=60, help="Frame rate")
    parser.add_argument(
        "--duration", type=int, help="Override duration in ms (optional)"
    )
    parser.add_argument("--audio", help="Path to audio file to merge (optional)")
    parser.add_argument("--gpu", "-g", action="store_true", help="Use GPU acceleration")

    args = parser.parse_args()

    if not os.path.exists(args.osb_path):
        print(f"Error: OSB file '{args.osb_path}' does not exist.")
        exit(1)

    basepath = os.path.dirname(args.osb_path)

    print(f"Parsing storyboard: {args.osb_path}")
    sb_parser = StoryboardParser()
    storyboard = sb_parser.parse(args.osb_path)

    engine = StateEngine(storyboard)

    total_duration = args.duration if args.duration else get_video_duration(storyboard)
    print(f"Total video duration: {total_duration} ms")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-s",
        f"{args.width}x{args.height}",
        "-pix_fmt",
        "rgba",
        "-r",
        str(args.fps),
        "-i",
        "-",  # Input from stdin
        "-c:v",
        "libx264",  # Video codec
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",  # Output pixel format
        "-crf",
        "23",  # Quality
        args.output,
    ]

    print(f"Starting ffmpeg with command: {' '.join(ffmpeg_cmd)}")
    total_frames = (total_duration * args.fps) // 1000 + 1
    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    if args.gpu:
        print("Using GPU acceleration for rendering.")

        renderer = SkiaRendererGpu(
            engine, AssetLoader(base_path=basepath), args.width, args.height
        )
        try:
            for i in range(total_frames):
                time_ms = int(i * 1000 / args.fps)
                frame = renderer.render_frame(time_ms)
                process.stdin.write(frame.tobytes())

        except KeyboardInterrupt:
            print("Rendering interrupted by user.")
        except Exception as e:
            print(f"An error occurred during rendering: {e}")
        finally:
            if process.stdin:
                process.stdin.close()
            process.wait()
            print(f"Video saved to {args.output}")

    else:
        cpu_count = max(1, multiprocessing.cpu_count() - 1)

        print(
            f"Using {cpu_count} CPU cores for rendering, total frames: {total_frames}"
        )

        tasks = [int(i * 1000 / args.fps) for i in range(total_frames)]

        try:
            with multiprocessing.Pool(
                processes=cpu_count,
                initializer=init_worker,
                initargs=(engine, basepath, args.width, args.height),
            ) as pool:
                result_iter = pool.imap(render_frame_worker, tasks, chunksize=10)

                for frame_bytes in result_iter:
                    process.stdin.write(frame_bytes)

        except KeyboardInterrupt:
            print("Rendering interrupted by user.")
        except Exception as e:
            print(f"An error occurred during rendering: {e}")
        finally:
            if process.stdin:
                process.stdin.close()
            process.wait()
            print(f"Video saved to {args.output}")

    if args.audio and os.path.exists(args.audio):
        print(f"Merging audio from {args.audio}")
        temp_output = args.output + ".temp.mp4"
        os.rename(args.output, temp_output)

        ffmpeg_audio_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            temp_output,
            "-i",
            args.audio,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            args.output,
        ]

        subprocess.run(
            ffmpeg_audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        os.remove(temp_output)
        print(f"Final video with audio saved to {args.output}")
    else:
        print(f"Done! Video saved to {args.output}, no audio merged.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
