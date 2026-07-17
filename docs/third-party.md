# Third-party

Framewright is MIT-licensed. The items below come from other authors and keep their own licenses.

## Vendored code

| What | Where | License |
|---|---|---|
| [video-creator/ffmpeg-mcp](https://github.com/video-creator/ffmpeg-mcp) | `servers/assets/frame_extractor/` | MIT (see its `LICENSE`) |

## Models (downloaded by `scripts/fetch_models.py`, not in git)

| Model | Source | License |
|---|---|---|
| ISNet anime-seg | [SkyTNT/anime-segmentation](https://github.com/SkyTNT/anime-segmentation) | Apache-2.0 |
| U2-Net | [xuebinqin/U-2-Net](https://github.com/xuebinqin/U-2-Net), ONNX via [rembg](https://github.com/danielgatis/rembg) | Apache-2.0 |
| Real-ESRGAN ncnn-vulkan | [xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | BSD-3-Clause |
| faster-whisper | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT |

## Fonts

Bundled in `servers/assets/text_overlay/`: Anton, Bebas Neue, Montserrat, Oswald, Poppins, from [Google Fonts](https://fonts.google.com), SIL Open Font License.

## Libraries

ffmpeg, librosa, PySceneDetect, ONNX Runtime, Pillow, numpy, and the MCP Python SDK. Each is installed as a dependency under its own license.

## Related Resolve projects

Earlier versions bundled these. They were removed from the repo and are credited here instead. Use them alongside Framewright:

| Project | What it is | License |
|---|---|---|
| [tmoroney/auto-subs](https://github.com/tmoroney/auto-subs) | Local AI subtitle generator with Resolve, Premiere Pro and After Effects integration | MIT |
| [X-Raym/DaVinci-Resolve-Scripts](https://github.com/X-Raym/DaVinci-Resolve-Scripts) | Lua scripts for editing, markers, media pool and timelines | see repo |
| [IgorRidanovic/DaVinciResolve-DynamicText](https://github.com/IgorRidanovic/DaVinciResolve-DynamicText) | Fusion title templates driven by external data | MIT |
| [Greenysmac/awesome-davinci-resolve](https://github.com/Greenysmac/awesome-davinci-resolve) | Curated list of Resolve plugins, DCTLs, scripts and tools | CC0 |
| [thatcherfreeman/resolve-scripts](https://github.com/thatcherfreeman/resolve-scripts) | Python scripts for Resolve and Fusion | see repo |
| [olegkupshukov/claude-resolve](https://github.com/olegkupshukov/claude-resolve) | AI terminal plugin for Resolve Studio that generates motion graphics | MIT |
