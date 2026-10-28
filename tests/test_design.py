"""Checks for the 2.0 design system: colour contrast (WCAG 2.1 AA), the Studio chart style,
the dark-paper colour steps and the drawn skin (no window needed).

    python tests/test_design.py
"""
from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from plotstudio import fonts  # noqa: E402
from plotstudio.engine import STUDIO_COLORS, StyleSettings, studio_rc  # noqa: E402
from plotstudio.paper import INK_PAPER, PAPER, STUDIO_DARK, apply_dark_paper, apply_paper  # noqa: E402
from plotstudio.skin import draw_icon, grow, shape, ICONS  # noqa: E402
from plotstudio.theme import DARK, INK_DARK, INK_LIGHT, LIGHT, STYLES, WIDGET_BG_KEYS, WIDGET_FG_KEYS  # noqa: E402

failures = []


def check(cond, text):
    if not cond:
        failures.append(text)
        print("FAIL", text)


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color):
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# text colour, background, minimum ratio (4.5 text, 3 for outlines and the focus ring)
PAIRS = [
    ("text", "panel", 4.5), ("text", "bg", 4.5), ("text", "field", 4.5), ("text", "raised", 4.5),
    ("text", "hover", 4.5), ("text", "select", 4.5), ("text", "accent_soft", 4.5), ("text", "card_hover", 4.5),
    ("muted", "panel", 4.5), ("muted", "bg", 4.5), ("muted", "raised", 4.5), ("muted", "field", 4.5),
    ("faint", "panel", 4.5), ("faint", "bg", 4.5), ("faint", "hover", 4.5), ("faint", "card_hover", 4.5),
    ("accent", "panel", 4.5), ("accent", "bg", 4.5), ("accent", "accent_soft", 4.5),
    ("on_accent", "accent", 4.5), ("on_accent", "accent_hover", 4.5), ("on_accent", "accent_pressed", 4.5),
    ("danger", "panel", 4.5), ("warn", "panel", 4.5), ("ok", "panel", 4.5),
    ("sev_warn", "panel", 3.0), ("sev_check", "panel", 3.0),
    ("danger", "danger_soft", 4.5), ("warn", "warn_soft", 4.5),
    ("tip_fg", "tip_bg", 4.5),
    ("input_border", "panel", 3.0), ("input_border", "field", 3.0),
    ("focus_ring", "panel", 3.0), ("focus_ring", "bg", 3.0),
]


def test_contrast():
    for name, pal in (("light", LIGHT), ("dark", DARK), ("ink light", INK_LIGHT), ("ink dark", INK_DARK)):
        for fg, bg, need in PAIRS:
            ratio = contrast(pal[fg], pal[bg])
            check(ratio >= need, f"{name}: {fg} on {bg} is {ratio:.2f}:1, needs {need}:1")


def test_dark_paper_matches_cards():
    check(PAPER["face"].lower() == DARK["panel"].lower(), "dark graph paper = dark card colour")
    check(INK_PAPER["face"].lower() == INK_DARK["panel"].lower(), "ink dark graph paper = ink dark card colour")


def test_every_style_has_every_role_once():
    # the live switch traces a widget's colour back to its role: within a palette each role's colour is unique
    for style, looks in STYLES.items():
        for mode, pal in looks.items():
            check(set(pal) == set(LIGHT), f"{style} {mode}: same roles as the default light look")
            for keys in (WIDGET_BG_KEYS, WIDGET_FG_KEYS):
                values = [pal[k].lower() for k in keys]
                check(len(set(values)) == len(values), f"{style} {mode}: widget colours are unique per role")


def test_graph_paper_adds_minor_lines_only_to_number_axes_with_a_grid():
    import matplotlib.pyplot as plt
    fig, (a, b) = plt.subplots(1, 2)
    a.plot([0, 1, 2], [3, 1, 2]); a.grid(True)
    b.bar(["x", "y"], [1, 2]); b.grid(True, axis="y")
    apply_paper(fig, dark=False, ink=True)
    fig.canvas.draw()
    check(all(t.tick1line.get_markersize() == 0 for t in a.xaxis.get_minor_ticks()), "no minor tick marks")
    check(len(a.yaxis.get_minorticklocs()) > 0 and len(b.xaxis.get_minorticklocs()) == 0,
          "minor lines on the number axes, none on the category axis")
    plt.close(fig)


def test_studio_palette():
    check(len(STUDIO_COLORS) == 8 and len(set(STUDIO_COLORS)) == 8, "8 distinct Studio colours")
    check(set(STUDIO_DARK) == set(STUDIO_COLORS), "every Studio colour has a dark-paper step")
    for light, dark in STUDIO_DARK.items():
        check(contrast(dark, PAPER["face"]) >= 3.0, f"dark step {dark} keeps 3:1 on the dark paper")


def test_studio_rc_keys_exist():
    rc = matplotlib.rcParams
    for context in ("paper", "notebook", "talk", "poster"):
        for key in studio_rc(context):
            check(key in rc, f"rcParams has {key}")
    talk, note = studio_rc("talk"), studio_rc("notebook")
    check(talk["lines.linewidth"] > note["lines.linewidth"], "line width follows the text size setting")
    check(note["lines.linewidth"] <= 1.5, "Studio lines are thin")


def test_exported_style_runs_without_plex():
    """The style block in an exported script must run quietly where IBM Plex is not installed."""
    code = "\n".join(StyleSettings().code())
    script = textwrap.dedent('''
        import logging, warnings, io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
        log = io.StringIO()
        logging.getLogger("matplotlib.font_manager").addHandler(logging.StreamHandler(log))
        warnings.simplefilter("error")
    ''') + code + textwrap.dedent('''
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [3, 1, 2], label="a")
        ax.set_title("Title")
        ax.legend()
        fig.canvas.draw()
        assert "findfont" not in log.getvalue(), log.getvalue()
        print("quiet")
    ''')
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "style_check.py"
        path.write_text(script, encoding="utf-8")
        done = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=120)
    check(done.returncode == 0 and "quiet" in done.stdout,
          f"exported style block runs without font warnings:\n{done.stdout}\n{done.stderr[-800:]}")


def test_dark_paper_steps_studio_lines():
    import matplotlib.pyplot as plt
    exec("\n".join(StyleSettings().code()), {"plt": plt, "sns": __import__("seaborn")})
    fig, ax = plt.subplots()
    lines = [ax.plot([0, 1], [i, i + 1])[0] for i in range(3)]
    apply_dark_paper(fig)
    for line, light in zip(lines, STUDIO_COLORS):
        got = matplotlib.colors.to_hex(line.get_color())
        check(got == STUDIO_DARK[light], f"line {light} -> {STUDIO_DARK[light]} on dark paper (got {got})")
    plt.close("all")
    matplotlib.rcdefaults()


def test_skin_pictures():
    img = shape(40, 30, 8, fill=(255, 0, 0, 255), border=(0, 0, 0, 255), margin=3)
    check(img.size == (40, 30), "shape() keeps the requested size")
    check(img.getpixel((0, 0))[3] == 0, "outside the rounded corner is see-through")
    check(img.getpixel((20, 15))[:3] == (255, 0, 0), "the middle is filled")
    big = grow(img, (12, 12, 12, 12), (200, 60))
    check(big.size == (200, 60), "grow() stretches to the new size")
    check(big.getpixel((0, 0)) == img.getpixel((0, 0)) and big.getpixel((199, 59)) == img.getpixel((39, 29)),
          "grow() keeps the corners")
    check(big.getpixel((100, 30)) == img.getpixel((20, 15)), "grow() repeats the middle")
    for name in ICONS:
        icon = draw_icon(name, 18, "#000000")
        check(icon.size == (18, 18) and icon.getbbox() is not None, f"icon {name} draws something")


def test_fonts_bundled():
    names = {f.name for f in fonts.font_files()}
    for face in ("IBMPlexSans-Regular.ttf", "IBMPlexSans-SemiBold.ttf", "IBMPlexMono-Regular.ttf"):
        check(face in names, f"{face} is bundled")
    check((fonts.FONT_DIR / "OFL-IBM-Plex.txt").is_file(), "the font licence is bundled")
    check(fonts.register_for_matplotlib(), "Plex registers with matplotlib")
    from matplotlib import font_manager
    path = font_manager.findfont(font_manager.FontProperties(family="IBM Plex Sans", weight="semibold"),
                                 fallback_to_default=False)
    check("IBMPlexSans-SemiBold" in path, f"matplotlib finds Plex SemiBold ({path})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILURE(S)'}")
    sys.exit(1 if failures else 0)
