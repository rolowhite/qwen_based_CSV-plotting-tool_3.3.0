"""Render the small preview pictures shown on the gallery cards (and the app icon).

Each graph gets a light picture (assets/thumbs) and a dark-paper one (assets/thumbs_dark),
drawn with the default (Studio) chart style and with rounded, see-through corners.
Run again after adding a graph type:

    python -m plotstudio.thumbnails
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from .data import RowSettings, load_csv  # noqa: E402
from .engine import LabelSettings, StyleSettings, build_plot, run_plot  # noqa: E402
from .graphs import GRAPHS, suggest  # noqa: E402
from .paper import PAPER, apply_dark_paper  # noqa: E402

HERE = Path(__file__).resolve().parent
SAMPLES = HERE.parent / "samples"
OUT = HERE / "assets" / "thumbs"
OUT_DARK = HERE / "assets" / "thumbs_dark"

A, T, S, P, D, X = ("airline_demo.csv", "training_log.csv", "store_sales.csv", "model_predictions.csv",
                    "digits_8x8.csv", "surface_xyz.csv")
DEMO = {  # graph id: (sample file, column choices, option choices)
    "line": (T, {"x": "epoch", "y": ["train_loss", "val_loss"]}, {}),
    "scatter": (S, {"x": "temperature", "y": "sales", "color": "store"}, {"alpha": 0.6, "size": 18}),
    "bar": (A, {"x": "Class", "y": "Flight Distance", "hue": "satisfaction"}, {}),
    "area": (T, {"x": "epoch", "y": ["train_loss", "val_loss"]}, {}),
    "pie": (A, {"labels": "Class"}, {"donut": True}),
    "errorbar": (X, {"x": "x", "y": "z"}, {"capsize": 2}),
    "hist": (A, {"cols": ["Age"], "hue": "satisfaction"}, {"bins": 25}),
    "kde": (A, {"cols": ["Flight Distance"], "hue": "Class"}, {}),
    "box": (A, {"y": ["Age"], "x": "Class", "hue": "satisfaction"}, {}),
    "violin": (A, {"y": ["Age"], "x": "Class", "hue": "Gender"}, {"split": True}),
    "strip": (S, {"y": ["sales"], "x": "store", "hue": None}, {"size": 2.5}),
    "ecdf": (A, {"cols": ["Age"], "hue": "Class"}, {}),
    "qq": (A, {"cols": ["Flight Distance"]}, {}),
    "regression": (A, {"x": "Departure Delay in Minutes", "y": "Arrival Delay in Minutes"}, {"equation": False}),
    "joint": (S, {"x": "temperature", "y": "sales", "hue": "store"}, {}),
    "hexbin": (A, {"x": "Age", "y": "Flight Distance"}, {"gridsize": 18}),
    "kde2d": (S, {"x": "temperature", "y": "sales"}, {}),
    "pairplot": (S, {"cols": ["sales", "customers", "temperature"], "hue": "store"}, {}),
    "corr": (S, {"cols": ["sales", "customers", "promo", "temperature"]}, {"annot": "no"}),
    "target_corr": (A, {"target": "satisfaction"}, {}),
    "count": (A, {"col": "Class", "hue": "satisfaction"}, {"labels": "none", "orient": "vertical"}),
    "missing": (A, {"cols": ["Gender", "Age", "Class", "Arrival Delay in Minutes", "satisfaction"]},
                {"only_missing": False, "sort": False}),
    "pivot": (A, {"rows": "Inflight wifi service", "cols": "Online boarding", "value": None}, {"annot": "no"}),
    "confusion": (P, {"actual": "y_true", "predicted": "model_a_pred"}, {}),
    "roc": (P, {"actual": "y_true", "scores": ["model_a_proba", "model_b_proba"]}, {}),
    "images": (D, {}, {"count": 16}),
    "contour": (X, {"x": "x", "y": "y", "z": "z"}, {"style": "filled_lines", "cmap": "RdGy"}),
    "scatter3d": (X, {"x": "x", "y": "y", "z": "z", "color": "z"}, {"size": 6}),
    "surface3d": (X, {"x": "x", "y": "y", "z": "z"}, {}),
    "facet": (S, {"x": "temperature", "y": "sales", "col": "store", "row": None, "hue": None},
              {"kind": "scatter"}),
}


def strip_text(fig):
    """Remove every label, tick label, legend and annotation: thumbnails only show shapes."""
    if getattr(fig, "_suptitle", None) is not None:
        fig._suptitle.set_text("")
    for legend in list(fig.legends):
        legend.remove()
    for ax in fig.axes:
        ax.set_title("")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(labelbottom=False, labelleft=False, labelright=False, labeltop=False, length=0)
        if hasattr(ax, "set_zlabel"):
            ax.set_zlabel("")
            ax.zaxis.set_ticklabels([])
            ax.xaxis.set_ticklabels([])
            ax.yaxis.set_ticklabels([])
        if ax.get_legend() is not None:
            ax.get_legend().remove()
        for text in list(ax.texts):
            text.remove()


def render(graph, datasets) -> plt.Figure:
    name, sel_over, opt_over = DEMO.get(graph.id, (A, {}, {}))
    ds = datasets.get(name) or datasets.setdefault(name, load_csv(SAMPLES / name))
    sel = {**suggest(graph, ds), **sel_over}
    built = build_plot(graph, ds, sel, opt_over, RowSettings(auto_sample=True), StyleSettings(),
                       LabelSettings(show_title=False))
    fig, _w, _s = run_plot(built)
    strip_text(fig)
    fig.set_size_inches(4.0, 2.6)
    axes3d = [ax for ax in fig.axes if hasattr(ax, "set_zlabel")]
    if axes3d:  # let 3D plots fill the small picture
        fig.set_layout_engine("none")
        for ax in fig.axes:
            if ax not in axes3d:
                ax.remove()
        axes3d[0].set_position((-0.18, -0.13, 1.2, 1.24))
    if fig.get_layout_engine() is None:
        try:
            fig.tight_layout(pad=0.4)
        except Exception:  # noqa: BLE001
            pass
    return fig


def save_rounded(fig, path: Path, dpi: int, face: str, radius: int):
    """Save the figure as a PNG whose corners are rounded (transparent outside the curve)."""
    from PIL import Image, ImageDraw
    buf = io.BytesIO()
    fig.savefig(buf, dpi=dpi, facecolor=face, format="png")
    img = Image.open(io.BytesIO(buf.getvalue())).convert("RGBA")
    k = 4
    mask = Image.new("L", (img.width * k, img.height * k), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width * k - 1, img.height * k - 1), radius=radius * k,
                                           fill=255)
    img.putalpha(mask.resize(img.size, Image.LANCZOS))
    img.save(path, optimize=True)


def make_icon(path: Path):
    fig = plt.figure(figsize=(2.56, 2.56), dpi=100)
    fig.patch.set_alpha(0)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    tile = FancyBboxPatch((0.06, 0.06), 0.88, 0.88, boxstyle="round,pad=0,rounding_size=0.2",
                          facecolor="none", edgecolor="none")
    ax.add_patch(tile)
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    coral = LinearSegmentedColormap.from_list("coral", ["#f58b66", "#c8461f"])     # the app's accent, lit from above
    ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1), cmap=coral, extent=(0.06, 0.94, 0.06, 0.94),
              aspect="auto", clip_path=tile, zorder=0)
    for x, h in ((0.24, 0.30), (0.42, 0.48), (0.60, 0.38), (0.78, 0.60)):
        ax.add_patch(FancyBboxPatch((x - 0.06, 0.2), 0.12, h, boxstyle="round,pad=0,rounding_size=0.03",
                                    facecolor="white", edgecolor="none", alpha=0.95))
    ax.plot([0.2, 0.42, 0.6, 0.8], [0.62, 0.74, 0.66, 0.86], color="#fbbf24", linewidth=6, solid_capstyle="round")
    ax.scatter([0.2, 0.42, 0.6, 0.8], [0.62, 0.74, 0.66, 0.86], s=110, color="#fbbf24", zorder=3)
    fig.savefig(path, transparent=True)
    plt.close(fig)
    try:  # .ico for Windows shortcuts
        from PIL import Image
        Image.open(path).save(path.with_suffix(".ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
    except Exception:  # noqa: BLE001
        pass


def main(ids=None):
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_DARK.mkdir(parents=True, exist_ok=True)
    make_icon(HERE / "assets" / "icon.png")
    datasets = {}
    for graph in GRAPHS:
        if ids and graph.id not in ids:
            continue
        try:
            fig = render(graph, datasets)
            save_rounded(fig, OUT / f"{graph.id}.png", 50, "white", 8)
            save_rounded(fig, OUT / f"{graph.id}@2x.png", 100, "white", 16)
            plt.close(fig)
            fig = render(graph, datasets)
            apply_dark_paper(fig)
            save_rounded(fig, OUT_DARK / f"{graph.id}.png", 50, PAPER["face"], 8)
            save_rounded(fig, OUT_DARK / f"{graph.id}@2x.png", 100, PAPER["face"], 16)
            plt.close(fig)
            print("ok  ", graph.id)
        except Exception as exc:  # noqa: BLE001
            print("FAIL", graph.id, type(exc).__name__, exc)


if __name__ == "__main__":
    main(sys.argv[1:])
