"""Download model weights into <repo>/models/.

Usage:
    python scripts/fetch_models.py               # all models
    python scripts/fetch_models.py isnet u2net   # pick some
    python scripts/fetch_models.py --force       # re-download

Stdlib only, so it runs before any `uv sync`.
"""
from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

_ESRGAN_BASE = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-"
_ESRGAN_OS = {"Windows": "windows", "Linux": "ubuntu", "Darwin": "macos"}

MODELS_SPEC = {
    "isnet": {
        "desc": "ISNet anime segmentation (style=anime)",
        "url": "https://huggingface.co/skytnt/anime-seg/resolve/main/isnetis.onnx",
        "dest": MODELS / "isnet" / "isnetis.onnx",
        "sha256": "f15622d853e8260172812b657053460e20806f04b9e05147d49af7bed31a6e99",
    },
    "u2net": {
        "desc": "U2-Net general segmentation (style=general)",
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
        "dest": MODELS / "isnet" / "u2net.onnx",
        "sha256": "8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491",
    },
    "birefnet": {
        "desc": "BiRefNet-lite matting, sharper hair/edges (style=general_hq, ~224 MB)",
        "url": "https://huggingface.co/onnx-community/BiRefNet_lite-ONNX/resolve/main/onnx/model.onnx",
        "dest": MODELS / "isnet" / "birefnet_lite.onnx",
        "sha256": "5600024376f572a557870a5eb0afb1e5961636bef4e1e22132025467d0f03333",
    },
    "realesrgan": {
        "desc": "Real-ESRGAN ncnn-vulkan upscaler (binary + models)",
        "url": _ESRGAN_BASE + _ESRGAN_OS.get(platform.system(), "ubuntu") + ".zip",
        "dest": MODELS / "realesrgan",
        # Pinned for the Windows zip only; Linux/macOS zips are not pinned yet.
        "sha256": "abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d" if platform.system() == "Windows" else None,
        "unzip": True,
    },
}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "framewright-fetch-models"})
    with urllib.request.urlopen(req, timeout=60) as r, open(out, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if total:
                _log(f"\r  {done * 100 // total:3d}%  {done >> 20} / {total >> 20} MB")
    _log("")


def _flatten_unzip(zip_path: Path, dest: Path) -> None:
    """Extract, dropping a single top-level folder if the zip has one."""
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        tops = {n.split("/", 1)[0] for n in names}
        strip = len(tops) == 1 and all("/" in n for n in names)
        for n in names:
            rel = n.split("/", 1)[1] if strip else n
            target = (dest / rel).resolve()
            if dest.resolve() not in target.parents:
                raise RuntimeError(f"Unsafe path in zip: {n}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                dst.write(src.read())
    exe = dest / "realesrgan-ncnn-vulkan"
    if exe.exists():
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def fetch(name: str, force: bool) -> bool:
    spec = MODELS_SPEC[name]
    dest: Path = spec["dest"]
    unzip = spec.get("unzip", False)
    present = any(dest.iterdir()) if unzip and dest.is_dir() else dest.is_file()
    if present and not force:
        _log(f"[skip] {name}: already at {dest.relative_to(ROOT)}")
        return True

    _log(f"[get ] {name}: {spec['desc']}\n  {spec['url']}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_file = Path(tmp) / "download"
        try:
            _download(spec["url"], tmp_file)
        except Exception as e:  # network errors, 404s
            _log(f"[fail] {name}: {e}")
            return False

        digest = _sha256(tmp_file)
        if spec["sha256"] and digest != spec["sha256"]:
            _log(f"[fail] {name}: SHA256 mismatch\n  expected {spec['sha256']}\n  got      {digest}")
            return False
        _log(f"  sha256 {digest}" + ("  (verified)" if spec["sha256"] else "  (not pinned)"))

        if unzip:
            dest.mkdir(parents=True, exist_ok=True)
            _flatten_unzip(tmp_file, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp_file), dest)
    _log(f"[ ok ] {name} -> {dest.relative_to(ROOT)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Download Framewright model weights into models/.")
    ap.add_argument("names", nargs="*", help=f"models to fetch: {', '.join(MODELS_SPEC)} (default: all)")
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    ap.add_argument("--list", action="store_true", help="list models and exit")
    args = ap.parse_args()

    if args.list:
        for k, v in MODELS_SPEC.items():
            _log(f"{k:11s} {v['desc']}")
        return 0

    names = args.names or list(MODELS_SPEC)
    unknown = [n for n in names if n not in MODELS_SPEC]
    if unknown:
        ap.error(f"unknown model(s): {', '.join(unknown)}; choose from {', '.join(MODELS_SPEC)}")
    failed = [n for n in names if not fetch(n, args.force)]
    if failed:
        _log(f"Failed: {', '.join(failed)}. Check your network and retry.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
