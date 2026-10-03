# CPU-only image that installs every server and runs the smoke test (start each server, list its tools).
#   docker build -t framewright .
#   docker run --rm framewright
# Models are not baked in; mount them for real work: -v "$PWD/models:/app/models"
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /usr/local/bin/

WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never

COPY . .
# Skip the CUDA wheels; the CPU onnxruntime (pulled in by audio_analyzer) serves subject_extractor too.
RUN uv sync --frozen --all-packages --no-dev \
    --no-install-package onnxruntime-gpu \
    --no-install-package nvidia-cublas-cu12 \
    --no-install-package nvidia-cuda-nvrtc-cu12 \
    --no-install-package nvidia-cuda-runtime-cu12 \
    --no-install-package nvidia-cudnn-cu12 \
    --no-install-package nvidia-cufft-cu12 \
    --no-install-package nvidia-curand-cu12 \
    --no-install-package nvidia-nvjitlink-cu12

# The smoke test calls `uv run` per server; don't let it re-sync the GPU packages back in.
ENV UV_NO_SYNC=1 UV_FROZEN=1
CMD ["python", "scripts/smoke_test.py"]
