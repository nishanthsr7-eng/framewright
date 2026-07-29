import logging
import os

import numpy as np
import onnxruntime as ort
from PIL import Image

# Model registry. Weights live in <project root>/models/isnet/ (see scripts/fetch_models.py).
#   anime   - ISNet trained on anime characters (skytnt/anime-seg). Input: RGB / 255, 1024px letterbox.
#   general - U2-Net salient object model for live-action footage. Input: ImageNet-normalized, 320px.
#   general_hq - BiRefNet-lite matting, sharper hair/edges. Input: ImageNet-normalized, 1024px. Output: logits.
MODELS = {
    "anime": {"file": "isnetis.onnx", "size": 1024, "mean": (0.0, 0.0, 0.0), "std": (1.0, 1.0, 1.0), "letterbox": True},
    "general": {"file": "u2net.onnx", "size": 320, "mean": (0.485, 0.456, 0.406), "std": (0.229, 0.224, 0.225), "letterbox": False},
    "general_hq": {"file": "birefnet_lite.onnx", "size": 1024, "mean": (0.485, 0.456, 0.406), "std": (0.229, 0.224, 0.225),
                   "letterbox": False, "logits": True},
}

_sessions = {}


def _models_dir():
    path = os.path.abspath(os.path.dirname(__file__))
    while True:
        parent, name = os.path.split(path)
        if name == "servers":
            return os.path.join(parent, "models", "isnet")
        if parent == path:
            raise FileNotFoundError("Could not locate the project 'servers' folder to find models/")
        path = parent


def _providers():
    if hasattr(ort, "preload_dlls"):  # onnxruntime-gpu: load the pip-installed CUDA/cuDNN libs
        try:
            ort.preload_dlls()
        except Exception as e:
            logging.warning("CUDA libs not loaded, GPU may be unavailable: %s", e)
    available = ort.get_available_providers()
    preferred = ["CUDAExecutionProvider", "DmlExecutionProvider", "CoreMLExecutionProvider", "CPUExecutionProvider"]
    # HEURISTIC skips cuDNN's per-shape benchmark, which is slow and memory-hungry on big models (BiRefNet)
    cuda_opts = {"cudnn_conv_algo_search": "HEURISTIC"}
    return [(p, cuda_opts) if p == "CUDAExecutionProvider" else p for p in preferred if p in available]


def _get_session(style):
    if style not in MODELS:
        raise ValueError(f"Unknown style '{style}'. Use one of: {', '.join(MODELS)}")
    if style not in _sessions:
        path = os.path.join(_models_dir(), MODELS[style]["file"])
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Model not found: {path}. Run: python scripts/fetch_models.py")
        _sessions[style] = ort.InferenceSession(path, providers=_providers())
    return _sessions[style]


def get_mask(img: np.ndarray, style: str = "anime", size: int | None = None) -> np.ndarray:
    """img: HxWx3 uint8 RGB. Returns HxW float32 foreground probability in [0, 1]."""
    cfg = MODELS[style]
    session = _get_session(style)
    size = size or cfg["size"]
    h0, w0 = img.shape[:2]

    if cfg["letterbox"]:
        h, w = (size, max(int(size * w0 / h0), 1)) if h0 > w0 else (max(int(size * h0 / w0), 1), size)
        resized = np.asarray(Image.fromarray(img).resize((w, h), Image.BILINEAR), dtype=np.float32) / 255.0
        ph, pw = size - h, size - w
        inp = np.zeros((size, size, 3), dtype=np.float32)
        inp[ph // 2: ph // 2 + h, pw // 2: pw // 2 + w] = resized
    else:
        inp = np.asarray(Image.fromarray(img).resize((size, size), Image.BILINEAR), dtype=np.float32) / 255.0

    inp = (inp - np.array(cfg["mean"], dtype=np.float32)) / np.array(cfg["std"], dtype=np.float32)
    blob = inp.transpose(2, 0, 1)[np.newaxis].astype(np.float32)
    outputs = session.run(None, {session.get_inputs()[0].name: blob})
    pred = outputs[-1 if cfg.get("logits") else 0][0, 0]  # BiRefNet's final map is last; U2-Net/ISNet's is first

    if cfg.get("logits"):
        pred = 1.0 / (1.0 + np.exp(-pred))
    elif cfg["letterbox"]:
        pred = pred[ph // 2: ph // 2 + h, pw // 2: pw // 2 + w]
    else:
        lo, hi = float(pred.min()), float(pred.max())
        pred = (pred - lo) / (hi - lo + 1e-8)

    pred = np.clip(pred, 0.0, 1.0)
    pred = Image.fromarray((pred * 255).astype(np.uint8)).resize((w0, h0), Image.BILINEAR)
    return np.asarray(pred, dtype=np.float32) / 255.0


def smooth_mask(mask, arr, prev, strength):
    """Blend with the previous frame's mask where the image barely changed, to stop flicker.

    Moving pixels keep the fresh mask, so there's no ghost trail behind the subject.
    """
    if prev is None or strength <= 0:
        return mask
    prev_arr, prev_mask = prev
    if prev_mask.shape != mask.shape:
        return mask
    diff = np.abs(arr.astype(np.float32) - prev_arr.astype(np.float32)).mean(axis=2) / 255.0
    weight = strength * np.clip(1.0 - diff / 0.08, 0.0, 1.0)
    return weight * prev_mask + (1.0 - weight) * mask


def split_subject_and_background(image_path, subject_path, background_path=None, style="anime", size=None,
                                 threshold=0.0, prev=None, smoothing=0.0):
    """Write an RGBA cut-out of the subject (and optionally the background with the subject removed).

    Returns (frame, smoothed_mask) to pass as `prev` for the next frame.
    """
    arr = np.array(Image.open(image_path).convert("RGB"))
    mask = smooth_mask(get_mask(arr, style=style, size=size), arr, prev, smoothing)
    state = (arr, mask)
    if threshold > 0:
        mask = (mask > threshold).astype(np.float32)
    alpha = (mask * 255).astype(np.uint8)
    Image.fromarray(np.dstack([arr, alpha]), "RGBA").save(subject_path)
    if background_path:
        Image.fromarray(np.dstack([arr, 255 - alpha]), "RGBA").save(background_path)
    return state
