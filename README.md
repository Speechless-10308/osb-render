<h1 align="center">OSBoard</h1>  
A high-performance osu! storyboard renderer — convert beatmap storyboards into MP4 videos.

![The Logo](banner.png)

## How to use?


1. Select your `.osu` file (yes plz `.osu` file), then it will automatically detect audios and the storyboard.
2. Select a folder to save the output video via the "Save As" button. 
3. Configurate your width, height and FPS. (Plz enable GPU Acceleration, way more faster and less bugs.)
4. Start Rendering!

## Use from source
Install uv on your PC.
```shell
uv sync
```
Use the tool with the following command (to use gpu accelaration and CLI version):
```shell
uv run main.py [osu_path] -o [output_path] --width 1920 --height 1080 --gpu
```

Use the following command to run a GUI version:
```shell
uv run app.py
```
Note that it is **osu_path**, the program will automatically detect the existence of audio and storyboard.

## TODO
- [x] An application with gui. (Partially done, with a lot of unknown bugs.)
- [ ] Some unknown bugs maybe...
- [ ] A good looking README.

## Benchmark

Run the benchmark against the reference beatmap set:

```shell
# CPU (default 1920x1080 @ 60 fps)
uv run tests/benchmark.py

# Custom resolution / framerate
uv run tests/benchmark.py --width 1280 --height 720 --fps 30

# GPU acceleration
uv run tests/benchmark.py --gpu --width 1920 --height 1080 --fps 60
```

Results are printed to the console and also written to `bench_results.md`.

### Reference Results

Here I provide a benchmark result of the reference beatmap set on my machine (Ryzen 7 9600 + RTX 5060). Note that the render time may vary a lot on different machines and configurations, so please run the benchmark yourself to get a more accurate result.

| Beatmap | Duration | Resolution | FPS | Render Time |
| :-- | :-- | :-- | :-- | :-- |
| [TWC Sound Team Strike Back Squad - BUZZ CUTZ](https://osu.ppy.sh/beatmapsets/2367508#mania/5154426) | 9:54 | 1920×1080 | 60 | 34.8 s |
| [Laur - SEV-26](https://osu.ppy.sh/beatmapsets/2508618#mania/5525561) | 6:54 | 1920×1080 | 60 | 28.9 s |
| [a_hisa - Alexithymia Lupinus Tokei no Heya to Seishin Sekai](https://osu.ppy.sh/beatmapsets/1054045#osu/2202493) | 10:37 | 1920×1080 | 60 | 2 m 48.3 s |

*Add the map you want to benchmark in `tests/benchmark.py` and run `uv run tests/benchmark.py --gpu` to get a benchmark result.*

## Acknowledgements
This project is powered by [glfw](https://www.glfw.org/), [skia](https://skia.org/) and [PySide6](https://pypi.org/project/PySide6/). We are thanks to their awesome work!

---
These are just some entertainment pieces I made in my spare time from research. Forgive me, my boss!!!
