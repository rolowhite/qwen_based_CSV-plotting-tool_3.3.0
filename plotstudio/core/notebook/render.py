"""Library exercises as HTML pages, shown in the system browser.

Markdown is turned into HTML here (markdown-it-py with the $...$ / $$...$$ plugin, so the TeX inside math is
kept as it is); the page then draws the math with the KaTeX copy in plotstudio/assets/katex. Nothing is
fetched from the internet. One page per chapter, so "Exercise N.M" links work as plain links, also across
chapters. Pages are written to a cache folder that depends on the library's content and the look.
"""
from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path
from typing import Iterable, List, Optional

from .library import Exercise, Library
from . import provenance

RENDER_VERSION = 1
ASSETS = Path(__file__).resolve().parents[2] / "assets"
KATEX = ASSETS / "katex"
FONTS = ASSETS / "fonts"
_MATH_SPLIT = re.compile(r'(<span class="math inline">.*?</span>|<div class="math block">.*?</div>)', re.S)
_MENTION = re.compile(r"\b(Exercises?)(\s+)(\d+\.\d+(?:(?:,\s*|\s+and\s+|\s*[–-]\s*)\d+\.\d+)*)")
_NUM = re.compile(r"\d+\.\d+")


class RenderUnavailable(RuntimeError):
    """markdown-it-py isn't installed."""


def how_to_enable() -> str:
    return "Showing solutions needs markdown-it-py: pip install -r requirements-notebook.txt"


def _markdown():
    try:
        from markdown_it import MarkdownIt
        from mdit_py_plugins.dollarmath import dollarmath_plugin
    except ImportError as exc:
        raise RenderUnavailable(how_to_enable()) from exc
    return MarkdownIt("commonmark", {"html": False}).enable("table").use(dollarmath_plugin, double_inline=True)


def page_name(book: str, chapter: int) -> str:
    return f"{re.sub(r'[^a-z0-9]+', '-', book.lower()).strip('-') or 'book'}-ch{chapter}.html"


def anchor(number: str) -> str:
    return f"ex-{number}"


def _link_mentions(fragment: str, library: Library, book: str) -> str:
    """'Exercise 3.31' in text (not in math) -> a link to that exercise, or a note saying which file it needs."""
    def one(number: str) -> str:
        target = library.get(number, book)
        if target is not None:
            return f'<a class="xref" href="{page_name(book, target.chapter)}#{anchor(number)}">{number}</a>'
        chapter = number.split(".")[0]
        return (f'<span class="xref missing" title="Exercise {number} is not loaded. Add the Chapter {chapter} '
                f'solution file to your library folder.">{number}</span>')

    def mention(m):
        return m.group(1) + m.group(2) + _NUM.sub(lambda n: one(n.group(0)), m.group(3))

    parts = _MATH_SPLIT.split(fragment)
    # odd parts are math; in the rest only text between tags is touched
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r">([^<]*)<", lambda t: ">" + _MENTION.sub(mention, t.group(1)) + "<", f">{parts[i]}<")[1:-1]
    return "".join(parts)


def markdown_html(text: str, library: Optional[Library] = None, book: str = "") -> str:
    out = _markdown().render(text)
    out = out.replace("<p>📘", '<p class="table-ref">📘')
    return _link_mentions(out, library, book) if library is not None else out


def _exercise_html(e: Exercise, library: Library) -> str:
    title = f"Exercise {e.number}" + (f" · {html.escape(e.title)}" if e.title else "")
    problem = (markdown_html(e.problem_md, library, e.book) if e.problem_md else
               '<p class="muted">This exercise has no separate problem text in your file.</p>')
    badge = provenance.for_exercise(e)
    note = markdown_html(badge.detail, library, e.book) if badge.detail else ""
    return (f'<section class="exercise" id="{anchor(e.number)}">\n<h2>{title}</h2>\n'
            f'<p class="topic">{html.escape(e.topic)}</p>\n<div class="problem">{problem}</div>\n'
            f'<div class="solution">{markdown_html(e.solution_md, library, e.book)}</div>\n'
            f'<div class="badge {badge.kind}"><strong>{html.escape(badge.label)}</strong>{note}</div>\n'
            '</section>\n')


def _font_faces() -> str:
    faces = [("IBMPlexSans-Regular.ttf", "IBM Plex Sans", 400, "normal"),
             ("IBMPlexSans-SemiBold.ttf", "IBM Plex Sans", 600, "normal"),
             ("IBMPlexSans-Bold.ttf", "IBM Plex Sans", 700, "normal"),
             ("IBMPlexSans-Italic.ttf", "IBM Plex Sans", 400, "italic"),
             ("IBMPlexMono-Regular.ttf", "IBM Plex Mono", 400, "normal")]
    return "".join(f"@font-face{{font-family:'{fam}';src:url('{(FONTS / f).as_uri()}');font-weight:{w};"
                   f"font-style:{s}}}" for f, fam, w, s in faces if (FONTS / f).is_file())


# colours follow the app's theme tokens (theme.py LIGHT / DARK)
CSS = """
:root{--bg:#f1f3f8;--panel:#ffffff;--text:#1a2030;--muted:#535c70;--border:#e2e6ee;--accent:#b8461f;
--soft:#fbece6;--ok:#067647;--ok-soft:#ecfdf3;--warn:#8a4b08;--warn-soft:#fff8e6;--code:#f7f8fb}
:root[data-theme=dark]{--bg:#121214;--panel:#1c1c1f;--text:#ededf0;--muted:#a6a6b0;--border:#2b2b30;
--accent:#f2764b;--soft:#35231e;--ok:#4ade80;--ok-soft:#13301e;--warn:#f6b04a;--warn-soft:#36290f;--code:#242428}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 'IBM Plex Sans',system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--panel);border-bottom:1px solid var(--border);
padding:10px 16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
header b{margin-right:10px} header a{color:var(--muted);text-decoration:none;padding:2px 8px;border-radius:999px}
header a.on{background:var(--soft);color:var(--accent);font-weight:600}
main{max-width:880px;margin:0 auto;padding:16px}
.exercise{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:18px 22px;
margin:16px 0;scroll-margin-top:64px}
.exercise:target{border-color:var(--accent);box-shadow:0 0 0 3px var(--soft)}
h1{font-size:22px;margin:8px 0} h2{font-size:19px;margin:0}
.topic{color:var(--muted);font-size:13px;margin:2px 0 12px}
.problem{background:var(--soft);border-radius:10px;padding:2px 14px;margin-bottom:12px}
.muted{color:var(--muted)}
table{border-collapse:collapse;margin:8px 0;display:block;overflow-x:auto;max-width:100%}
td,th{border:1px solid var(--border);padding:4px 10px;text-align:left}
pre{background:var(--code);padding:10px;border-radius:8px;overflow-x:auto;font:13px/1.4 'IBM Plex Mono',monospace}
code{font-family:'IBM Plex Mono',monospace}
.katex-display{overflow-x:auto;overflow-y:hidden;padding:2px 0}
.table-ref{background:var(--code);border-left:3px solid var(--muted);padding:6px 10px;border-radius:6px}
.badge{border-radius:10px;padding:8px 12px;margin-top:12px;font-size:14px}
.badge p{margin:4px 0 0}
.badge.verified{background:var(--ok-soft);color:var(--ok)} .badge.verified p{color:var(--text)}
.badge.caution{background:var(--warn-soft);color:var(--warn)} .badge.caution p{color:var(--text)}
.badge.unchecked{background:var(--code);color:var(--muted)}
a.xref{color:var(--accent)} .xref.missing{border-bottom:1px dotted var(--muted);cursor:help}
.math.error{color:#b42318}
@media (max-width:600px){main{padding:8px}.exercise{padding:14px}}
"""

SCRIPT = """document.querySelectorAll('.math').forEach(function(e){try{katex.render(e.textContent,e,
{displayMode:e.classList.contains('block'),throwOnError:true})}catch(err){e.classList.add('error');e.title=err.message}});
if(location.hash){var t=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(t)t.scrollIntoView();}"""


def _page(title: str, body: str, dark: bool) -> str:
    """A whole HTML page: the theme's look, the bundled fonts and KaTeX, and `body` (already HTML)."""
    return (f'<!doctype html><html lang="en" data-theme="{"dark" if dark else "light"}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>'
            f'<link rel="stylesheet" href="{(KATEX / "katex.min.css").as_uri()}">'
            f'<style>{_font_faces()}{CSS}</style>'
            f'<script src="{(KATEX / "katex.min.js").as_uri()}"></script></head><body>'
            f'{body}<script>{SCRIPT}</script></body></html>')


def chapter_page(library: Library, book: str, chapter: int, dark: bool = False) -> str:
    exercises = [e for e in library.exercises if e.book == book and e.chapter == chapter]
    nav = "".join(f'<a href="{page_name(book, c)}" class="{"on" if c == chapter else ""}">{c}</a>'
                  for c in library.chapters(book))
    edition = next((e.edition for e in exercises if e.edition), "")
    heading = f"{html.escape(book.title())} {html.escape(edition)} · Chapter {chapter}".replace("  ", " ")
    return _page(heading, f'<header><b>{heading}</b>{nav}</header><main>'
                 + "".join(_exercise_html(e, library) for e in exercises) + '</main>', dark)


def answer_page(markdown: str, dark: bool = False) -> str:
    """One Notebook answer as a page, for "Open in browser" (the math drawn by KaTeX)."""
    return _page("Solution", f'<main><section class="exercise">{markdown_html(markdown)}</section></main>', dark)


def library_digest(library: Library) -> str:
    h = hashlib.sha256(f"{RENDER_VERSION}".encode())
    for e in library.exercises:
        h.update(f"{e.key}\0{e.problem_md}\0{e.solution_md}\0{e.checker_note}\0{e.caution_note}\0".encode())
    return h.hexdigest()[:16]


class Pages:
    """Writes the chapter pages once per library content and look, and says which file opens an exercise.
    shortcut: folders of older library versions are left in place (a few MB each); prune them if that grows."""

    def __init__(self, library: Library, folder: Path, dark: bool = False):
        self.library = library
        self.dark = dark
        self.folder = Path(folder) / f"{library_digest(library)}-{'dark' if dark else 'light'}"

    def ensure(self, books: Optional[Iterable[str]] = None) -> List[Path]:
        """Write every chapter page that isn't there yet (all books, or `books`)."""
        written = []
        self.folder.mkdir(parents=True, exist_ok=True)
        for book in books or sorted({e.book for e in self.library.exercises}):
            for chapter in self.library.chapters(book):
                path = self.folder / page_name(book, chapter)
                if not path.is_file():
                    path.write_text(chapter_page(self.library, book, chapter, self.dark), encoding="utf-8")
                    written.append(path)
        return written

    def opener(self, exercise: Exercise) -> Path:
        """A small page that jumps to the exercise. Windows drops '#...' when a file URL is handed to the
        browser, so the jump is done by the page itself."""
        self.ensure([exercise.book])
        target = f"{page_name(exercise.book, exercise.chapter)}#{anchor(exercise.number)}"
        path = self.folder / "open.html"
        path.write_text(f'<!doctype html><meta charset="utf-8"><title>Exercise {exercise.number}</title>'
                        f'<script>location.replace({target!r});</script>'
                        f'<a href="{target}">Open Exercise {exercise.number}</a>', encoding="utf-8")
        return path

