"""Formulas drawn by mathtext: the rewrite into its LaTeX subset, the PNG, and a clear error for the rest."""
import io

import pytest

from plotstudio.core.notebook import render, tex

TYPICAL = [r"\frac{7}{12}\cdot\frac{6}{11}", r"\binom{52}{5}", r"\sum_{i=1}^n x_i", r"\bar{x}=2.833", r"\sigma^2",
           r"\sqrt{n}", r"P(A \mid B)", r"x \geq 0", r"a \le b", r"\text{ and }", r"\tfrac12", r"\dfrac{1}{4}",
           r"\frac1n\sum x_i", r"\sqrt x", r"\mathbf v", r"\boxed{\mu=\mathbf{0.88}}", r"\left(\tfrac12\right)^5",
           r"\big[P(A)+P(B)\big]", r"\sum\lvert\delta_i\rvert", r"W=(\#H)-(\#T)"]


@pytest.mark.parametrize("source, prepared", [
    (r"a\le b\ge c", r"a\leq b\geq c"),
    (r"\left(x\right)\leq", r"\left(x\right)\leq"),            # \left and \leq are not \le
    (r"\tfrac12+\dfrac{2k}3", r"\frac{1}{2}+\dfrac{2k}{3}"),
    (r"\frac{\tfrac13(1)}{\tfrac13\cdot\tfrac12}", r"\frac{\frac{1}{3}(1)}{\frac{1}{3}\cdot\frac{1}{2}}"),
    (r"\sqrt x+\sqrt[3]{y}+\sqrt\pi", r"\sqrt{x}+\sqrt[3]{y}+\sqrt{\pi}"),
    (r"\mathbf v,\ \binom43", r"\mathbf{v},\ \binom{4}{3}"),
    (r"\boxed{x}\Big(y\Big)", r"{x}(y)"),
    ("a\nb", "a b"),
])
def test_prepare_rewrites_into_what_mathtext_knows(source, prepared):
    assert tex.prepare(source) == prepared


@pytest.mark.parametrize("formula", TYPICAL)
def test_typical_library_formulas_are_drawn(formula):
    from PIL import Image
    image = Image.open(io.BytesIO(tex.png(formula, 12, 96, "#1a2030")))
    assert image.width > 4 and image.height > 4


def test_bigger_dpi_gives_a_bigger_picture_and_the_colour_is_used():
    from PIL import Image
    small = Image.open(io.BytesIO(tex.png("x^2", 12, 96, "#ff0000"))).convert("RGBA")
    big = Image.open(io.BytesIO(tex.png("x^2", 12, 192, "#ff0000"))).convert("RGBA")
    assert big.width > small.width * 1.6
    assert small.getpixel((0, 0))[3] == 0                                   # transparent around the ink
    assert max(small.get_flattened_data(), key=lambda px: px[3])[:3] == (255, 0, 0)


def _size(formula):
    from PIL import Image
    return Image.open(io.BytesIO(tex.png(formula, 12, 96, "#000000"))).size


def test_environments_are_laid_out_as_grids():
    one_row = _size(r"F(x)=\begin{cases}0,&x<0\end{cases}")
    two_rows = _size(r"F(x)=\begin{cases}0,&x<0\\1,&x\ge0\end{cases}")
    assert two_rows[1] > one_row[1] * 1.6
    plain = _size(r"\begin{matrix}1&2\\3&4\end{matrix}")
    bracketed = _size(r"\begin{bmatrix}1&2\\3&4\end{bmatrix}")
    assert bracketed[0] > plain[0] and bracketed[1] >= plain[1]
    pair = _size(r"X'X=\begin{bmatrix}10&59\\59&447\end{bmatrix},\qquad X'y=\begin{bmatrix}489\\3876\end{bmatrix}")
    assert pair[0] > bracketed[0] * 2


def test_what_mathtext_cant_draw_raises_a_tex_error():
    for formula in (r"\frac{1}{", r"a\xrightarrow{n}b", r"\begin{cases}\begin{matrix}1\end{matrix}\end{cases}"):
        with pytest.raises(tex.TexError):
            tex.png(formula)


def test_answer_page_draws_math_in_the_browser():
    page = render.answer_page("**Problem.** Find $P(X<0.2)$.\n\n$$F(x)=1-e^{-8x}$$", dark=True)
    assert 'data-theme="dark"' in page and "katex.min.js" in page
    assert '<span class="math inline">P(X&lt;0.2)</span>' in page and "<strong>Problem.</strong>" in page
