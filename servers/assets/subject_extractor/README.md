# Subject Extractor

Cut the main subject out of every frame in a folder and save transparent PNGs, ready for compositing.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `extract_subject` | `input_folder`, `style`=general, `with_background`, `threshold`=0, `skip_existing`=True | folder of RGBA PNGs (+ optional backgrounds) |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- onnxruntime; models `models/isnet/isnetis.onnx` and `models/isnet/u2net.onnx` (`python scripts/fetch_models.py isnet u2net`)
- Install: `uv sync --directory servers/assets/subject_extractor`
- Run: `uv run --directory servers/assets/subject_extractor subject-extractor-mcp`

## Example call

```json
{
  "tool": "extract_subject",
  "arguments": {
    "input_folder": "output/clip/frames",
    "style": "anime"
  }
}
```

## Anime vs general footage

`style="anime"` uses ISNet (anime-seg) at 1024px; `style="general"` uses U2-Net at 320px for people and objects. Use `threshold` > 0 for hard edges.

## Credits

- Anime model: [SkyTNT/anime-segmentation](https://github.com/SkyTNT/anime-segmentation) (ISNet, Apache-2.0)
- General model: [xuebinqin/U-2-Net](https://github.com/xuebinqin/U-2-Net) (Apache-2.0), ONNX export from [rembg](https://github.com/danielgatis/rembg)
