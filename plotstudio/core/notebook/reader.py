"""The problem(s) in a picture or a PDF page, read by a local vision model (Ollama).

The model is asked to copy, not to solve, and to answer in a fixed JSON shape (Ollama's `format`), which is
parsed with json.loads and checked; nothing it writes is ever run. A digital PDF page also sends its text
layer as a hint, because those characters are exact.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import ollama

Box = Tuple[float, float, float, float]      # left, top, right, bottom in image pixels
PDF_DPI = 150                                # the page picture shown in the Notebook
READ_DPI = 300                               # a page is drawn again this sharp for the reader
MAX_IMAGE_BYTES = 50 * 1024 * 1024
# room for a big picture (~2,500 tokens) plus the reply; the cap ends a model that loops instead of answering
OPTIONS = {"temperature": 0, "num_ctx": 8192, "num_predict": 3072}
_RULE = re.compile(r"^\s*\|?(\s*:?-{3,}:?\s*\|)*\s*:?-{3,}:?\s*\|?\s*$")       # a table's |---|---| line

SCHEMA = {
    "type": "object",
    "properties": {
        "problems": {"type": "array", "items": {
            "type": "object",
            "properties": {"label": {"type": "string"}, "markdown": {"type": "string"}},
            "required": ["label", "markdown"]}},
        "unreadable": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["problems", "unreadable"],
}

PROMPT = """Copy the statistics problem(s) in this picture exactly. Do not solve them.
- One entry per problem, in the order printed. "label": its number as printed (for example "3.13"), or "".
- "markdown": the whole problem text without the label. Write math as LaTeX in $...$ (inline) or $$...$$
  (display) and tables as Markdown tables (with the |---| line). Copy every number, unit and table value exactly as printed:
  do not round, convert, simplify or correct anything. Include data shown in a figure.
- Leave out page headers, page numbers and cut-off pieces of other problems.
- "unreadable": short notes on any part you could not read; an empty list if none."""


@dataclass(frozen=True)
class Problem:
    label: str
    markdown: str


@dataclass
class Reading:
    problems: List[Problem] = field(default_factory=list)
    unreadable: List[str] = field(default_factory=list)
    raw: str = ""
    seconds: float = 0.0


def table_rules(markdown: str) -> str:
    """Add the |---| line a Markdown table needs after its first row, when the model left it out."""
    lines, out = markdown.split("\n"), []
    for i, line in enumerate(lines):
        out.append(line)
        starts = line.lstrip().startswith("|") and (i == 0 or not lines[i - 1].lstrip().startswith("|"))
        if starts and not (i + 1 < len(lines) and _RULE.match(lines[i + 1])):
            out.append("|" + "---|" * (line.strip().strip("|").count("|") + 1))
    return "\n".join(out)


def parse(raw: str) -> Reading:
    """The model's JSON reply as a Reading; OllamaError when it isn't the shape that was asked for."""
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw)       # some models fence JSON even when told not to
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ollama.OllamaError("The reading model's reply wasn't valid JSON.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("problems"), list):
        raise ollama.OllamaError("The reading model's reply doesn't list the problems.")
    problems = []
    for p in data["problems"]:
        if not isinstance(p, dict) or not isinstance(p.get("markdown"), str):
            raise ollama.OllamaError("The reading model sent a problem without its text.")
        label = p.get("label") if isinstance(p.get("label"), str) else ""
        if p["markdown"].strip():
            problems.append(Problem(label.strip(), table_rules(p["markdown"].strip())))
    unreadable = [u.strip() for u in data.get("unreadable") or [] if isinstance(u, str) and u.strip()]
    return Reading(problems, unreadable, raw)


def read(chat: "ollama.Chat", model: str, image, hint: str = "", think: Optional[bool] = None,
         long_side: Optional[int] = None) -> Reading:
    """Read a PIL image. `hint` is a PDF text layer; `long_side` sends the picture at that size instead."""
    prompt = PROMPT
    if hint.strip():
        prompt += ("\n\nThe page's text layer is below (exact characters, maybe out of order). Use its numbers "
                   "exactly:\n<<<\n" + hint.strip()[:6000] + "\n>>>")
    start = time.perf_counter()
    raw = chat.text(model, [{"role": "user", "content": prompt,
                             "images": [ollama.prepare_image(image, long_side)]}], format=SCHEMA, think=think,
                    options=OPTIONS)
    reading = parse(raw)
    reading.seconds = round(time.perf_counter() - start, 2)
    return reading


# --------------------------------------------------------------------------------------------- PDFs --
def text_layer(doc, index: int, box: Optional[Box] = None, view=None) -> str:
    """The text layer of page `index` of an open PdfDoc ('' if it has none or copying is not allowed).
    `box` is in the pixels of the picture drawn with `view`."""
    info = doc.page_info(index)
    if info.kind not in ("digital", "mixed") or not doc.may_copy_text:
        return ""
    with doc.page(index) as page:
        textpage = page.get_textpage()
        try:
            if box is not None and view is not None:
                x0, y0, x1, y1 = view.box_to_user(box)
                text = textpage.get_text_bounded(left=x0, bottom=y0, right=x1, top=y1)
            else:
                text = textpage.get_text_range()
        finally:
            textpage.close()
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def page_image(doc, index: int, box: Optional[Box] = None, view=None):
    """Page `index` drawn at READ_DPI (only the `box` part, given in the pixels of `view`'s picture)."""
    image, sharp = doc.render(index, dpi=READ_DPI)
    if box is not None and view is not None:
        k = sharp.scale / view.scale
        image = image.crop(tuple(int(round(v * k)) for v in box))
    return image
