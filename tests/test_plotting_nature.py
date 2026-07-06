from pathlib import Path

import matplotlib.pyplot as plt

from thinfilm.plotting import PAPER, apply_plot_style, save_publication_figure, style_axis


def test_publication_export_writes_editable_vector_bundle(tmp_path: Path):
    apply_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax in axes:
        style_axis(ax)
        ax.plot([0, 1], [0, 1])
        ax.set_title("Panel")
    files = save_publication_figure(fig, tmp_path / "figure.png", close=True)
    assert all(Path(path).is_file() for path in files.values())
    svg = Path(files["svg"]).read_text(encoding="utf-8")
    assert "<text" in svg
    assert "nature-panel-label" in svg


def test_nature_style_uses_white_background_and_minimal_spines():
    apply_plot_style()
    fig, ax = plt.subplots()
    style_axis(ax)
    assert PAPER == "#FFFFFF"
    assert not ax.spines["top"].get_visible()
    assert not ax.spines["right"].get_visible()
    plt.close(fig)
