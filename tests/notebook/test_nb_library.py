"""Reading the solution library: exercises, topics, checker notes, load problems, the cache, read-only files."""
import hashlib
import json

import pytest

import nb_fixtures as fx
from plotstudio.core.notebook import library, lookup, render


@pytest.fixture
def sample(tmp_path):
    return fx.write_sample(tmp_path / "lib")


def test_sample_parses_with_topics_notes_and_titles(sample):
    lib = library.load([sample.parent])
    assert [e.number for e in lib.exercises] == ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2"]
    e11, e12, e13, e14 = (lib.get(n) for n in ("1.1", "1.2", "1.3", "1.4"))
    assert e11.book == "sample" and e11.edition == "1st" and e11.chapter == 1
    assert e11.topic == "Sample — Chapter 1, Section 1.1: Coins and boxes"
    assert lib.get("2.1").topic == "Sample — Chapter 2, Section 2.1: Sample mean"
    assert e11.problem_md.startswith("**Problem:** A box holds 7 red")
    assert e11.checker_note == "python gives 0.31818."
    assert "Checker" not in e11.solution_md and e11.solution_md.startswith("$$P=")
    assert e12.caution_note == "the key prints 0.53; we keep four places." and not e12.checker_note
    assert e13.title == "Lamp Test"
    assert "| $P(T>t)$ |" in e13.problem_md, "a table right after the problem belongs to it"
    assert e13.solution_md.startswith("$$F(t)")
    assert e13.table_refs == ("📘 *Table check (Table A.0, placeholder): 0.1353 ✓.*",)
    assert not e14.has_problem and "20,000" in e14.solution_md


def test_load_problems_are_reported_with_lines_and_loading_goes_on(sample, tmp_path):
    (sample.parent / "no_front_matter.md").write_text("### Exercise 5.1\ntext\n", encoding="utf-8")
    lib = library.load([sample.parent, tmp_path / "missing"])
    text = [str(p) for p in lib.problems]
    assert any("Exercise 1.4 has no **Problem:**" in t and "line" in t for t in text)
    assert any("Exercise 2.2 appears again" in t for t in text)
    assert any("no_front_matter.md" in t and "no front matter" in t for t in text)
    assert any("folder not found" in t for t in text)
    assert len(lib.exercises) == 6


def test_the_index_cache_is_used_and_refreshed(sample, tmp_path):
    cache = tmp_path / "index.json"
    first = library.load([sample], cache_path=cache)
    saved = json.loads(cache.read_text(encoding="utf-8"))
    assert saved["version"] == library.INDEX_VERSION and len(saved["files"]) == 1
    digest = next(iter(saved["files"]))
    saved["files"][digest]["exercises"][0]["topic"] = "from the cache"
    cache.write_text(json.dumps(saved), encoding="utf-8")
    assert library.load([sample], cache_path=cache).get("1.1").topic == "from the cache"
    sample.write_text(fx.SAMPLE.replace("7 red", "8 red"), encoding="utf-8")       # changed file: parsed again
    again = library.load([sample], cache_path=cache)
    assert "8 red" in again.get("1.1").problem_md and again.get("1.1").topic == first.get("1.1").topic


def test_library_files_are_never_written(sample, tmp_path):
    before = (sample.stat().st_mtime_ns, hashlib.sha256(sample.read_bytes()).hexdigest())
    lib = library.load([sample.parent], cache_path=tmp_path / "cache" / "index.json")
    lookup.Index(lib).lookup("A box holds 7 red and 5 blue marbles")
    pytest.importorskip("markdown_it")
    render.Pages(lib, tmp_path / "pages").ensure()
    assert (sample.stat().st_mtime_ns, hashlib.sha256(sample.read_bytes()).hexdigest()) == before
    assert sorted(p.name for p in sample.parent.iterdir()) == ["Sample_Solutions.md"]


def test_neighbours_and_chapters(sample):
    lib = library.load([sample])
    assert lib.neighbour(lib.get("1.4"), 1).number == "2.1"
    assert lib.neighbour(lib.get("1.1"), -1) is None
    assert lib.chapters("sample") == [1, 2]


def test_the_real_chapter_3_has_81_exercises():
    lib = library.load([fx.real_library()])
    ch3 = [e for e in lib.exercises if e.book == "walpole" and e.chapter == 3]
    if not ch3:
        pytest.skip("the library at NOTEBOOK_LIBRARY has no Walpole chapter 3")
    assert len(ch3) == 81
    assert [e.number for e in ch3[:3]] == ["3.1", "3.2", "3.3"]
    assert all(e.topic.startswith("Walpole") for e in ch3)
    assert sum(bool(e.checker_note or e.caution_note) for e in ch3) >= 70
    assert not [p for p in lib.problems if "Chapter 3" in p.message]
