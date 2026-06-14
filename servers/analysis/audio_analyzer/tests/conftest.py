import pytest

SR = 22050


@pytest.fixture(scope="session")
def click_track(tmp_path_factory):
    """8 s of short clicks at 120 BPM, louder clicks on every 4th beat."""
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    y = np.zeros(SR * 8, dtype=np.float32)
    click = np.sin(2 * np.pi * 1000 * np.arange(int(SR * 0.03)) / SR).astype(np.float32)
    click *= np.linspace(1.0, 0.0, click.size, dtype=np.float32)
    for n, t in enumerate(np.arange(0.5, 7.5, 0.5)):
        i = int(t * SR)
        y[i : i + click.size] += click * (1.0 if n % 4 == 0 else 0.4)
    path = tmp_path_factory.mktemp("audio") / "clicks.wav"
    sf.write(path, y, SR)
    return str(path)
