"""Reading problems with a vision model (a fake Ollama here), and a PDF page's text layer."""
import json

import pytest

from fake_ollama import FakeOllama
from plotstudio.core.notebook import ollama, reader

VISION = {"vl": ["completion", "vision"]}


def _reply(*problems, unreadable=()):
    return json.dumps({"problems": [{"label": l, "markdown": m} for l, m in problems], "unreadable": list(unreadable)})


def _picture():
    from PIL import Image
    return Image.new("RGB", (900, 300), "white")


def test_one_call_returns_every_problem_in_order():
    reply = _reply(("3.13", "The distribution of $X$ is 0.41, 0.37 and 0.22."), ("3.14", "Find $P(X<0.2)$."))
    with FakeOllama(VISION, replies=[reply]) as fake:
        reading = reader.read(ollama.Chat(fake.url), "vl", _picture(), think=False)
        sent = fake.requests[0]
    assert [p.label for p in reading.problems] == ["3.13", "3.14"]
    assert reading.problems[0].markdown.startswith("The distribution")
    assert reading.unreadable == [] and len(fake.requests) == 1
    assert sent["format"] == reader.SCHEMA and sent["think"] is False and sent["options"] == reader.OPTIONS
    assert sent["messages"][0]["images"] and "Do not solve" in sent["messages"][0]["content"]


def test_the_text_layer_hint_and_the_size_are_sent():
    import base64
    import io
    from PIL import Image
    with FakeOllama(VISION, replies=[_reply()]) as fake:
        reader.read(ollama.Chat(fake.url), "vl", _picture(), hint="4.1 A coin is tossed 3 times.", long_side=1800)
        message = fake.requests[0]["messages"][0]
    assert "4.1 A coin is tossed 3 times." in message["content"]
    assert Image.open(io.BytesIO(base64.b64decode(message["images"][0]))).size == (1800, 600)


@pytest.mark.parametrize("raw, words", [("not json", "valid JSON"), ('{"text": "hi"}', "doesn't list"),
                                        ('{"problems": [{"label": "1"}]}', "without its text")])
def test_a_reply_in_the_wrong_shape_is_a_clear_error(raw, words):
    with pytest.raises(ollama.OllamaError, match=words):
        reader.parse(raw)


def test_a_table_without_its_rule_line_gets_one():
    read = "has the distribution below.\n\n| $x$ | 0 | 1 | 2 |\n| $f(x)$ | 0.5 | 0.3 | 0.2 |\n\nFind the CDF."
    fixed = reader.table_rules(read)
    assert fixed.split("\n")[3] == "|---|---|---|---|"
    assert reader.table_rules(fixed) == fixed                      # a table that has it is left alone
    assert reader.table_rules("no table here") == "no table here"
    from plotstudio.core.notebook import render
    assert "<table>" in render.markdown_html(fixed)
    assert reader.parse(_reply(("", read))).problems[0].markdown == fixed


def test_doubly_escaped_line_breaks_and_a_repeated_problem_are_repaired():
    # what qwen3-vl:8b-instruct really sent for one picture of Exercise 3.13 (shortened)
    raw = ('{"problems": [{"label": "", "markdown": "has the distribution below.\\\\n\\\\n| x | 0 | 1 |\\\\n|---|---|---|'
           '\\\\n| f(x) | 0.41 | 0.59 |"}, {"label": "", "markdown": "has the distribution  below.\\\\n\\\\n| x | 0 | 1 '
           '|\\\\n|---|---|---|\\\\n| f(x) | 0.41 | 0.59 |"}], "unreadable": []}')
    reading = reader.parse(raw)
    assert len(reading.problems) == 1
    assert reading.problems[0].markdown == "has the distribution below.\n\n| x | 0 | 1 |\n|---|---|---|\n| f(x) | 0.41 | 0.59 |"
    assert reader.line_breaks(r"$\nu \neq 0$ and \$5\n$\nabla$") == "$\\nu \\neq 0$ and \\$5\n$\\nabla$"


def test_a_label_repeated_in_the_text_is_dropped_there():
    reading = reader.parse(_reply(("1.31", "1.31 Consider Exercise 1.28."), ("2.4", "2.40 is a value.")))
    assert [p.markdown for p in reading.problems] == ["Consider Exercise 1.28.", "2.40 is a value."]


def test_fenced_json_empty_problems_and_unreadable_notes():
    raw = "```json\n" + _reply(("", "Find the mean."), ("", "  "), unreadable=["the figure's axis"]) + "\n```"
    reading = reader.parse(raw)
    assert reading.problems == [reader.Problem("", "Find the mean.")]
    assert reading.unreadable == ["the figure's axis"]


def test_a_text_pdf_gives_its_text_layer_and_a_marked_area(tmp_path):
    # moved from the old test_nb_ocr.py: the text-layer code now lives in reader.py
    pytest.importorskip("pypdfium2")
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    from plotstudio.core.pdf_import.inspect import PdfDoc

    path = tmp_path / "problems.pdf"
    c = canvas.Canvas(str(path), pagesize=(600, 400))
    c.setFont("Helvetica", 14)
    c.drawString(40, 340, "4.1 First problem: a fair coin is tossed 3 times.")
    c.drawString(40, 120, "4.2 Second problem: the mean of 2, 4 and 9.")
    c.save()
    with PdfDoc(path) as doc:
        whole = reader.text_layer(doc, 0)
        assert "First problem" in whole and "Second problem" in whole
        _image, view = doc.render(0, dpi=reader.PDF_DPI)
        k = view.scale
        lower = (0, 250 * k, 600 * k, 400 * k)
        part = reader.text_layer(doc, 0, box=lower, view=view)
        assert "Second problem" in part and "First problem" not in part
        crop = reader.page_image(doc, 0, box=lower, view=view)
        assert crop.size == (round(600 * k * 2), round(150 * k * 2))       # READ_DPI is twice PDF_DPI
