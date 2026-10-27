"""The solution library: Markdown files with worked exercises, read into Exercise records.

The files are only read, never written. A file has front matter (book, edition, chapter, ...), chapters
start with `# ... Chapter N: ...`, the nearest `## ...` heading is the topic, and each exercise is a
`### Exercise N.M` block (an optional suffix like `(Monty Hall)` is its title). Inside a block:
  **Problem:** ...     the problem text (that paragraph plus any table right after it)
  ✔ *Checker: ...*     a verified result     ⚠ ...  a caution about the result
  📘 *...*             a table lookup (Appendix A)
One file per chapter and one file for the whole book both work.

Parsed files are cached in a JSON index keyed by each file's SHA-256, so a later start only re-reads
files that changed.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

INDEX_VERSION = 1
# the solutions that come with the app (Walpole 9th edition chapters 1-18, Lind 15th edition chapters 8-12); only read
_NOTEBOOK_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "notebook"
BUILT_IN = _NOTEBOOK_ASSETS / "Walpole_All_Chapters_Solutions.md"
BUILT_IN_FILES = (BUILT_IN, _NOTEBOOK_ASSETS / "Lind_Chapters_8_to_12_Solutions.md")
EXERCISE_RE = re.compile(r"^###\s+Exercise\s+(\d+)\.(\d+)\s*(?:\((.+)\))?\s*$")
CHAPTER_RE = re.compile(r"^#\s+.*?Chapter\s+(\d+)\b")
TOPIC_RE = re.compile(r"^##\s+(.+?)\s*$")
VERIFIED_MARK, CAUTION_MARK, TABLE_MARK = "✔", "⚠", "📘"


@dataclass(frozen=True)
class Exercise:
    book: str
    edition: str
    chapter: int
    number: str                     # "3.13"
    topic: str                      # the nearest ## heading
    problem_md: str                 # "" when the block has no **Problem:** (the solution text is matched then)
    solution_md: str                # the rest of the block, without the checker lines
    checker_note: str = ""          # the ✔ lines' text
    caution_note: str = ""          # the ⚠ lines' text
    table_refs: Tuple[str, ...] = ()
    title: str = ""                 # "Monty Hall" from "### Exercise 2.102 (Monty Hall)"
    source_file: str = ""
    line: int = 0                   # 1-based line of the ### heading

    @property
    def key(self) -> str:
        return f"{self.book}:{self.number}"

    @property
    def has_problem(self) -> bool:
        return bool(self.problem_md)

    @property
    def sort_key(self) -> Tuple[str, int, int]:
        major, minor = self.number.split(".")
        return self.book, int(major), int(minor)


@dataclass(frozen=True)
class LoadProblem:
    file: str
    line: int
    message: str

    def __str__(self):
        return f"{Path(self.file).name}, line {self.line}: {self.message}" if self.line else \
            f"{Path(self.file).name}: {self.message}"


@dataclass
class Library:
    exercises: List[Exercise] = field(default_factory=list)
    problems: List[LoadProblem] = field(default_factory=list)
    files: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.exercises.sort(key=lambda e: e.sort_key)
        self._by_key = {e.key: e for e in self.exercises}
        self._by_number: Dict[str, List[Exercise]] = {}
        for e in self.exercises:
            self._by_number.setdefault(e.number, []).append(e)

    def get(self, number: str, book: Optional[str] = None) -> Optional[Exercise]:
        """The exercise with this number (in `book`, or the first book that has it)."""
        if book:
            return self._by_key.get(f"{book}:{number}")
        found = self._by_number.get(number)
        return found[0] if found else None

    def all_with_number(self, number: str) -> List[Exercise]:
        return list(self._by_number.get(number, ()))

    def neighbour(self, exercise: Exercise, step: int) -> Optional[Exercise]:
        """The previous (-1) or next (+1) exercise of the same book."""
        i = self.exercises.index(exercise) + step
        if 0 <= i < len(self.exercises) and self.exercises[i].book == exercise.book:
            return self.exercises[i]
        return None

    def chapters(self, book: str) -> List[int]:
        return sorted({e.chapter for e in self.exercises if e.book == book})


# ---------------------------------------------------------------------------------------------- parsing --
def front_matter(text: str) -> Tuple[Dict[str, str], int]:
    """The `key: value` lines between the opening `---` lines, and the number of lines they use (0: none)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return meta, i + 1
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return {}, 0      # never closed: not front matter


def _split_problem(body: List[str]) -> Tuple[str, List[str]]:
    """The **Problem:** paragraph (plus a table right after it) and the remaining lines."""
    start = next((i for i, line in enumerate(body) if line.startswith("**Problem:**")), None)
    if start is None:
        return "", body
    end = start
    while end < len(body) and body[end].strip():
        end += 1
    # a table that follows after one blank line belongs to the problem ("has the distribution below")
    while end + 1 < len(body) and not body[end].strip() and body[end + 1].lstrip().startswith("|"):
        end += 1
        while end < len(body) and body[end].strip():
            end += 1
    problem = "\n".join(body[start:end]).strip()
    return problem, body[:start] + body[end:]


def _note_text(line: str, mark: str) -> str:
    """'✔ *Checker: python gives 3.79.*' -> 'python gives 3.79.'"""
    text = line[len(mark):].strip()
    if len(text) > 1 and text.startswith("*") and text.endswith("*"):
        text = text[1:-1].strip()
    return re.sub(r"^Checker(?: note)?:\s*", "", text)


def _exercise(meta, chapter, topic, number, title, body, path, line) -> Exercise:
    problem, rest = _split_problem(body)
    checks, cautions, kept = [], [], []
    for text in rest:
        stripped = text.strip()
        if stripped.startswith(VERIFIED_MARK):
            checks.append(_note_text(stripped, VERIFIED_MARK))
        elif stripped.startswith(CAUTION_MARK):
            cautions.append(_note_text(stripped, CAUTION_MARK))
        else:
            kept.append(text)
    while kept and kept[-1].strip() in ("", "---"):
        kept.pop()
    tables = tuple(t.strip() for t in kept if t.strip().startswith(TABLE_MARK))
    return Exercise(book=meta.get("book", "") or Path(path).stem.split("_")[0].lower(),
                    edition=meta.get("edition", ""), chapter=chapter, number=number, topic=topic,
                    problem_md=problem, solution_md="\n".join(kept).strip("\n"),
                    checker_note=" ".join(checks), caution_note=" ".join(cautions), table_refs=tables,
                    title=title or "", source_file=str(path), line=line)


def parse_text(text: str, path="<text>") -> Tuple[List[Exercise], List[LoadProblem]]:
    """Every exercise in one library file, and what could not be read (with its line)."""
    text = text.replace("\r\n", "\n").lstrip("﻿")
    meta, skip = front_matter(text)
    if not skip:
        return [], [LoadProblem(str(path), 1, "no front matter (--- book: ... ---) at the top; file skipped")]
    if not meta.get("book"):
        return [], [LoadProblem(str(path), 1, "the front matter has no 'book:'; file skipped")]
    exercises, problems = [], []
    chapter, topic = None, ""
    current = None          # (number, title, line, topic, body lines)
    seen = {}

    def close():
        if current is None:
            return
        number, title, line, at_topic, body = current
        ex = _exercise(meta, int(number.split(".")[0]), at_topic, number, title, body, path, line)
        if not ex.problem_md:
            problems.append(LoadProblem(str(path), line, f"Exercise {number} has no **Problem:** block; "
                                                         "its solution text is matched instead"))
        if number in seen:
            problems.append(LoadProblem(str(path), line, f"Exercise {number} appears again "
                                                         f"(first at line {seen[number]}); the first is kept"))
            return
        seen[number] = line
        exercises.append(ex)

    for i, line in enumerate(text.split("\n")[skip:], start=skip + 1):
        m = EXERCISE_RE.match(line)
        if m:
            close()
            current = (f"{int(m.group(1))}.{int(m.group(2))}", m.group(3), i, topic, [])
            if chapter is not None and int(m.group(1)) != chapter:
                problems.append(LoadProblem(str(path), i, f"Exercise {current[0]} is under the Chapter "
                                                          f"{chapter} heading"))
            continue
        if line.startswith("#") and not line.startswith("####"):
            close()
            current = None
            c = CHAPTER_RE.match(line)
            if c:
                chapter, topic = int(c.group(1)), ""
            t = TOPIC_RE.match(line)
            if t:
                topic = t.group(1)
            if line.startswith("### "):
                problems.append(LoadProblem(str(path), i, f"heading not read as an exercise: {line[:60]}"))
            continue
        if current is not None:
            current[4].append(line)
    close()
    if not exercises:
        problems.append(LoadProblem(str(path), 0, "no '### Exercise N.M' headings found"))
    return exercises, problems


# ------------------------------------------------------------------------------------------ the index --
def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def library_files(folders: Iterable) -> List[Path]:
    """Every *.md in the folders (a path to a single .md file also works), in a stable order."""
    found = []
    for folder in folders:
        p = Path(folder).expanduser()
        if p.is_file() and p.suffix.lower() == ".md":
            found.append(p)
        elif p.is_dir():
            found.extend(sorted(p.glob("*.md")))
    seen, out = set(), []
    for p in found:
        r = p.resolve()
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _to_record(e: Exercise) -> dict:
    d = dataclasses.asdict(e)
    d["table_refs"] = list(e.table_refs)
    return d


def _from_record(d: dict) -> Exercise:
    return Exercise(**{**d, "table_refs": tuple(d.get("table_refs", ()))})


def load(folders: Iterable, cache_path: Optional[Path] = None) -> Library:
    """Read every library file in `folders`, using (and refreshing) the cached index when given."""
    folders = list(folders)
    cache = {}
    if cache_path is not None:
        try:
            saved = json.loads(Path(cache_path).read_text(encoding="utf-8"))
            if saved.get("version") == INDEX_VERSION:
                cache = saved.get("files", {})
        except (OSError, ValueError, AttributeError):
            cache = {}
    exercises, problems, files, fresh = [], [], [], {}
    for folder in folders:
        if not Path(folder).expanduser().exists():
            problems.append(LoadProblem(str(folder), 0, "folder not found"))
    for path in library_files(folders):
        try:
            digest = file_hash(path)
        except OSError as exc:
            problems.append(LoadProblem(str(path), 0, f"can't read the file ({exc})"))
            continue
        entry = cache.get(digest)
        if entry is None:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                problems.append(LoadProblem(str(path), 0, f"can't read the file as UTF-8 text ({exc})"))
                continue
            found, issues = parse_text(text, path)
            entry = {"exercises": [_to_record(e) for e in found],
                     "problems": [dataclasses.asdict(p) for p in issues]}
        fresh[digest] = entry
        found = [_from_record(d) for d in entry["exercises"]]
        # the same file content moved elsewhere: point at where it is now
        found = [dataclasses.replace(e, source_file=str(path)) for e in found]
        exercises.extend(found)
        problems.extend(LoadProblem(**{**p, "file": str(path)}) for p in entry["problems"])
        files.append(str(path))
    # two files with the same book and exercise: keep the first, say so
    unique, seen = [], {}
    for e in exercises:
        if e.key in seen:
            problems.append(LoadProblem(e.source_file, e.line, f"Exercise {e.number} of '{e.book}' is also in "
                                                               f"{Path(seen[e.key]).name}; that one is kept"))
            continue
        seen[e.key] = e.source_file
        unique.append(e)
    if cache_path is not None and fresh != cache:
        try:
            Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
            Path(cache_path).write_text(json.dumps({"version": INDEX_VERSION, "files": fresh}), encoding="utf-8")
        except OSError as exc:
            problems.append(LoadProblem(str(cache_path), 0, f"couldn't save the index cache ({exc})"))
    return Library(unique, problems, files)
