<h1 align="center">Osb Render</h1>  
A simple osb render with lots of bugs and latency...

## How to use?
![The GUI Pic](assets/image.png)

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

## TODO
- [x] An application with gui. (Partially done, with a lot of unknown bugs.)
- [ ] Some unknown bugs maybe...
- [ ] A good looking README.

---
These are just some entertainment pieces I made in my spare time from research. Forgive me, my boss!!!
