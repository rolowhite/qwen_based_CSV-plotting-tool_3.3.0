"""Solution pages: Markdown with LaTeX, tables and $$ blocks, offline KaTeX, exercise links."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("markdown_it")
pytest.importorskip("mdit_py_plugins")

import nb_fixtures as fx  # noqa: E402
from plotstudio.core.notebook import library, render  # noqa: E402


@pytest.fixture
def lib(tmp_path):
    return library.load([fx.write_sample(tmp_path / "lib")])


def test_cases_table_and_display_math_keep_their_tex(lib):
    page = re.sub(r'(<div class="math block">)\s+|\s+(</div>)', r"\1\2", render.chapter_page(lib, "sample", 1))
    assert r'<div class="math block">F(t)=\begin{cases}0,&amp;t&lt;0\\1-e^{-4t},&amp;t\ge0\end{cases}</div>' in page
    assert "<table>" in page and "<td>0.1353</td>" in page
    assert r'<div class="math block">P=\frac{7}{12}\cdot\frac{6}{11}=\mathbf{0.3182}.</div>' in page
    assert '<p class="table-ref">📘' in page
    assert 'class="badge verified"' in page and 'class="badge caution"' in page


def test_the_page_works_offline(lib):
    page = render.chapter_page(lib, "sample", 1)
    assert not re.search(r"(src|href)=[\"']https?:", page), "nothing may come from the internet"
    for uri in re.findall(r"(?:src|href)=\"(file:[^\"]+)\"", page):
        assert Path(uri.replace("file:///", "").replace("%20", " ")).is_file(), uri
    assert len(list((render.KATEX / "fonts").glob("*.woff2"))) == 20


def test_exercise_mentions_become_links_or_say_what_is_missing(lib):
    page = render.chapter_page(lib, "sample", 2)
    assert '<a class="xref" href="sample-ch1.html#ex-1.1">1.1</a>' in page
    assert 'title="Exercise 9.9 is not loaded. Add the Chapter 9 solution file' in page


def test_links_are_not_made_inside_math(lib):
    out = render.markdown_html(r"See Exercise 1.1 and $\text{Exercise 1.1}$.", lib, "sample")
    assert out.count('class="xref"') == 1


def test_pages_and_the_opener(lib, tmp_path):
    pages = render.Pages(lib, tmp_path / "pages", dark=True)
    opener = pages.opener(lib.get("2.1"))
    assert sorted(p.name for p in pages.folder.glob("*.html")) == ["open.html", "sample-ch1.html", "sample-ch2.html"]
    assert "location.replace('sample-ch2.html#ex-2.1')" in opener.read_text(encoding="utf-8")
    assert 'data-theme="dark"' in (pages.folder / "sample-ch2.html").read_text(encoding="utf-8")
    assert pages.ensure() == [], "pages are written once"


def _browser():
    names = ["msedge", "chrome", "chromium", "chromium-browser", "google-chrome"]
    found = next((shutil.which(n) for n in names if shutil.which(n)), None)
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if not found and os.path.isfile(p):
            found = p
    return found


@pytest.mark.slow
def test_katex_draws_every_formula_in_a_real_browser(lib, tmp_path):
    browser = _browser()
    if browser is None:
        pytest.skip("no Edge or Chrome to run KaTeX in")
    page = tmp_path / "p.html"
    page.write_text(render.chapter_page(lib, "sample", 1).replace(
        "</body>", "<script>document.title='K'+document.querySelectorAll('.katex').length+'E'+"
                   "document.querySelectorAll('.math.error').length</script></body>"), encoding="utf-8")
    out = subprocess.run([browser, "--headless", "--disable-gpu", "--dump-dom", page.as_uri()],
                         capture_output=True, text=True, timeout=60).stdout
    title = re.search(r"<title>(K\d+E\d+)</title>", out)
    assert title, out[:500]
    drawn, errors = map(int, re.findall(r"\d+", title.group(1)))
    assert errors == 0 and drawn == page.read_text(encoding="utf-8").count('class="math ')
