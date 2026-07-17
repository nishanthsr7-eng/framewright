# Setup

## 1. Prerequisites

| Tool | Why | Install |
|---|---|---|
| ffmpeg + ffprobe | All video/audio processing | Windows: `winget install Gyan.FFmpeg` · macOS: `brew install ffmpeg` · Linux: your package manager |
| uv | Python env per server | `winget install astral-sh.uv` · or see [uv docs](https://docs.astral.sh/uv/) |
| Python 3.10+ | `scripts/fetch_models.py` | Any recent Python |

Check: `ffmpeg -version` and `ffprobe -version`.
Stabilization needs an ffmpeg build with `libvidstab`; alpha `.webm` output needs `libvpx`. Full builds (e.g. Gyan's on Windows) include both.

## 2. Models

```bash
python scripts/fetch_models.py           # all
python scripts/fetch_models.py --list    # what is available
```

| Model | Used by | Path |
|---|---|---|
| ISNet anime-seg (`isnetis.onnx`) | subject_extractor, `style="anime"` | `models/isnet/` |
| U2-Net (`u2net.onnx`) | subject_extractor, `style="general"` | `models/isnet/` |
| Real-ESRGAN ncnn-vulkan (binary + models) | frame_extractor `enhance_frames` | `models/realesrgan/` |
| faster-whisper | audio_analyzer `transcribe_audio` | downloaded automatically on first use |

Downloads are checked against pinned SHA256 hashes where available.

## 3. Install servers

One server:

```bash
uv sync --directory servers/render/effects
```

All servers (bash):

```bash
for d in servers/*/*/; do uv sync --directory "$d"; done
```

All servers (PowerShell):

```powershell
Get-ChildItem servers\*\* -Directory | ForEach-Object { uv sync --directory $_.FullName }
```

## 4. Connect an MCP client

```bash
cp .mcp.json.example .mcp.json
```

`.mcp.json` registers all 19 servers with relative paths, so open your MCP client from the repo root. Any MCP-capable client works. After changing server code, restart or reconnect the client so it reloads.

Run one server by hand to debug it:

```bash
uv run --directory servers/render/effects effects-mcp
```

## 5. DaVinci Resolve (optional)

1. Preferences → System → General → **External scripting using = Local**, then restart Resolve.
2. Install the scripts and templates: see [resolve.md](resolve.md#install).

## Inputs and outputs

- Put source media anywhere; `input/` at the repo root is ignored by git.
- Tools write to `output/` at the repo root by default.

## Performance

- Real-ESRGAN uses Vulkan: works on NVIDIA, AMD and Intel GPUs, no CUDA needed.
- Subject extraction runs on CPU via ONNX Runtime, about 1-2 s per frame. Split scenes first and only process the shots you need.
- Everything else runs on CPU through ffmpeg, librosa or Pillow.
