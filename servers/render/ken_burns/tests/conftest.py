import shutil

import pytest


@pytest.fixture(scope="session")
def photo(tmp_path_factory):
    """320x180 image: horizontal gradient so zooms and pans change the picture."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    x = np.linspace(0, 255, 320, dtype=np.uint8)
    arr = np.stack([np.tile(x, (180, 1)), np.tile(x[::-1], (180, 1)), np.full((180, 320), 80, np.uint8)], axis=-1)
    path = tmp_path_factory.mktemp("ken burns") / "photo.png"
    Image.fromarray(arr).save(path)
    return str(path)
