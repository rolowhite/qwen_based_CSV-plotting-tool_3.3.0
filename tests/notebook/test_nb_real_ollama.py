"""With the real local Ollama (skipped when it isn't running or has no vision model): a printed problem is read
with every number, and a sample-library problem drawn as a picture is answered from the library."""
import pytest

import nb_fixtures as fx
from plotstudio.core.notebook import library, lookup, ollama, reader, session

pytestmark = pytest.mark.ollama


@pytest.fixture(scope="module")
def model():
    try:
        found = ollama.models()
    except ollama.OllamaError as exc:
        pytest.skip(str(exc))
    name = ollama.pick(found, "vision", avoid="thinking")
    if name is None:
        pytest.skip("no Ollama model with the vision capability")
    return name, dict(found)[name]


def _picture(lines):
    from PIL import Image, ImageDraw, ImageFont
    from plotstudio.fonts import FONT_DIR
    img = Image.new("RGB", (1400, 90 + 60 * len(lines)), "white")
    font = ImageFont.truetype(str(FONT_DIR / "IBMPlexSans-Regular.ttf"), 34)
    ImageDraw.Draw(img).multiline_text((40, 40), "\n".join(lines), fill="black", font=font, spacing=24)
    return img


def test_a_printed_problem_is_read_with_every_number(model):
    name, caps = model
    lines = ["3.13 The number of imperfections per 10 meters of fabric", "has the distribution 0.41, 0.37, 0.16,",
             "0.05 and 0.01 for x = 0, 1, 2, 3, 4. Find the CDF."]
    reading = reader.read(ollama.Chat(), name, _picture(lines), think=False if "thinking" in caps else None)
    assert len(reading.problems) == 1
    numbers = lookup.numbers(reading.problems[0].markdown)
    for n in ("10", "0.41", "0.37", "0.16", "0.05", "0.01"):
        assert n in numbers, (n, reading.problems[0].markdown)


def test_a_library_problem_in_a_picture_is_answered(model, tmp_path):
    index = lookup.Index(library.load([fx.write_sample(tmp_path)]))
    lines = ["A box holds 7 red and 5 blue marbles. Two marbles are drawn", "without replacement. Find the "
             "probability that both are red."]
    turn = session.Turn(session.Source("p.png", _picture(lines)), index, wanted_model=model[0], pace=0)
    answers = turn.run(lambda event: None)
    assert turn.answers[0]["from"] == "library:sample:1.1", turn.reads[-1].raw
    assert "**Solution.**" in answers[0]
