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

Bundled in `servers/assets/text_overlay/fonts/` (24 families), from [Google Fonts](https://fonts.google.com), SIL Open Font License 1.1 (see `fonts/OFL.txt`) unless noted:

Anton, Archivo Black, Bangers, Bebas Neue, Black Ops One, Bungee, Caveat, Dancing Script, Fredoka, Inter, Lobster, Lora, Merriweather, Montserrat, Open Sans, Oswald, Pacifico, Permanent Marker (Apache-2.0), Playfair Display, Poppins, PT Serif, Roboto Condensed, Russo One, Teko.

## Demo media

Credits for the F1 demo footage and music: [CREDITS.md](../CREDITS.md).

## Libraries

ffmpeg, librosa, PySceneDetect, ONNX Runtime, Pillow, numpy and the MCP Python SDK. Each is installed as a dependency under its own license.
