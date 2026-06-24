import pytest

Image = pytest.importorskip("PIL.Image")
np = pytest.importorskip("numpy")
segmenter = pytest.importorskip("subject_extractor_mcp.segmenter")


class _FakeSession:
    """Stands in for an ONNX session: predicts foreground in the left half of the model input."""

    def __init__(self):
        self.blobs = []

    def get_inputs(self):
        class _Input:
            name = "input"

        return [_Input()]

    def run(self, _outputs, feeds):
        blob = feeds["input"]
        self.blobs.append(blob)
        size = blob.shape[-1]
        pred = np.zeros((1, 1, size, size), dtype=np.float32)
        pred[..., : size // 2] = 1.0
        return [pred]


@pytest.fixture
def fake_session(monkeypatch):
    sess = _FakeSession()
    monkeypatch.setattr(segmenter, "_sessions", {"anime": sess, "general": sess})
    return sess


@pytest.mark.parametrize("style", ["anime", "general"])
def test_mask_shape_and_range(fake_session, style):
    img = np.full((90, 160, 3), 128, dtype=np.uint8)
    mask = segmenter.get_mask(img, style=style, size=64)
    assert mask.shape == (90, 160) and mask.dtype == np.float32
    assert 0.0 <= mask.min() and mask.max() <= 1.0
    assert fake_session.blobs[-1].shape == (1, 3, 64, 64)


def test_general_style_finds_left_half(fake_session):
    mask = segmenter.get_mask(np.zeros((64, 64, 3), dtype=np.uint8), style="general", size=32)
    assert mask[:, :24].mean() > 0.9 and mask[:, 40:].mean() < 0.1


def test_anime_style_letterboxes(fake_session):
    segmenter.get_mask(np.full((50, 100, 3), 255, dtype=np.uint8), style="anime", size=64)
    blob = fake_session.blobs[-1][0]
    # 2:1 image in a square input: top and bottom rows are padding, middle rows hold the image.
    assert blob[:, 0].max() == 0.0 and blob[:, -1].max() == 0.0
    assert blob[:, 32].min() == pytest.approx(1.0)


def test_split_subject_and_background(fake_session, tmp_path):
    src, subj, bg = tmp_path / "in.png", tmp_path / "subj.png", tmp_path / "bg.png"
    Image.new("RGB", (64, 64), "white").save(src)
    segmenter.split_subject_and_background(str(src), str(subj), str(bg), style="general", size=32, threshold=0.5)
    a_subj = np.asarray(Image.open(subj))[..., 3]
    a_bg = np.asarray(Image.open(bg))[..., 3]
    assert Image.open(subj).mode == "RGBA"
    assert set(np.unique(a_subj)) <= {0, 255}
    assert np.array_equal(a_subj.astype(int) + a_bg, np.full((64, 64), 255))


def test_unknown_style_raises():
    with pytest.raises(ValueError):
        segmenter._get_session("cartoon")
