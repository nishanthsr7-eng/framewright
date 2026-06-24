import os

import numpy as np
import onnxruntime as ort
from PIL import Image

# Model registry. Weights live in <project root>/models/isnet/ (see scripts/fetch_models.py).
#   anime   - ISNet trained on anime characters (skytnt/anime-seg). Input: RGB / 255, 1024px letterbox.
#   general - U2-Net salient object model for live-action footage. Input: ImageNet-normalized, 320px.
MODELS = {
    "anime": {"file": "isnetis.onnx", "size": 1024, "mean": (0.0, 0.0, 0.0), "std": (1.0, 1.0, 1.0), "letterbox": True},
    "general": {"file": "u2net.onnx", "size": 320, "mean": (0.485, 0.456, 0.406), "std": (0.229, 0.224, 0.225), "letterbox": False},
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
    available = ort.get_available_providers()
    preferred = ["CUDAExecutionProvider", "DmlExecutionProvider", "CoreMLExecutionProvider", "CPUExecutionProvider"]
    return [p for p in preferred if p in available]


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
    pred = session.run(None, {session.get_inputs()[0].name: blob})[0][0, 0]

    if cfg["letterbox"]:
        pred = pred[ph // 2: ph // 2 + h, pw // 2: pw // 2 + w]
    else:
        lo, hi = float(pred.min()), float(pred.max())
        pred = (pred - lo) / (hi - lo + 1e-8)

    pred = np.clip(pred, 0.0, 1.0)
    pred = Image.fromarray((pred * 255).astype(np.uint8)).resize((w0, h0), Image.BILINEAR)
    return np.asarray(pred, dtype=np.float32) / 255.0


def split_subject_and_background(image_path, subject_path, background_path=None, style="anime", size=None, threshold=0.0):
    """Write an RGBA cut-out of the subject (and optionally the background with the subject removed)."""
    arr = np.array(Image.open(image_path).convert("RGB"))
    mask = get_mask(arr, style=style, size=size)
    if threshold > 0:
        mask = (mask > threshold).astype(np.float32)
    alpha = (mask * 255).astype(np.uint8)
    Image.fromarray(np.dstack([arr, alpha]), "RGBA").save(subject_path)
    if background_path:
        Image.fromarray(np.dstack([arr, 255 - alpha]), "RGBA").save(background_path)
