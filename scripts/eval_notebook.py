"""Measure the Notebook's reading and matching on your own solution library (the library is the answer key).

    python scripts/eval_notebook.py --library C:/path/Walpole_All_Chapters_Solutions.md --n 60

For a sample of exercises that have a **Problem:** block and a ✔ checker line, each problem is drawn as a
picture twice (a clean page drawn by the browser with KaTeX, and a tilted, blurred, JPEG "phone photo" of
it), then run through the same read -> match path as the app (session.Turn, a second read on a miss).
Reported: every number read right, the right exercise answered, wrong exercises answered (must be 0),
the text similarity and the seconds per picture. Pictures and eval_notebook.json go to --out (default
~/.csv_plot_studio/notebook/eval), never into the repo: they contain the book's problem text.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plotstudio.core.notebook import library, library_match, lookup, ollama, render, session  # noqa: E402

BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "msedge", "microsoft-edge", "chromium",
            "chromium-browser", "google-chrome"]


def find_browser(wanted: str = "") -> str:
    for name in ([wanted] if wanted else BROWSERS):
        path = name if Path(name).is_file() else shutil.which(name)
        if path:
            return path
    raise SystemExit("No Edge or Chromium found to draw the problems. Pass --browser PATH.")


def problem_text(e: library.Exercise) -> str:
    return e.problem_md.replace("**Problem:**", "", 1).strip()


def draw(browser: str, markdown: str, path: Path):
    """The problem drawn by the browser (KaTeX), cropped to the text."""
    from PIL import Image, ImageChops

    html = render._page("problem", f'<main style="max-width:760px"><div>{render.markdown_html(markdown)}</div>'
                                   '</main>', dark=False).replace("var(--bg)", "#ffffff")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "p.html"
        page.write_text(html, encoding="utf-8")
        shot = Path(tmp) / "shot.png"
        # its own profile, so a running Edge (or a stuck earlier run) can't block this one
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                        "--disable-extensions", f"--user-data-dir={Path(tmp) / 'profile'}", "--window-size=900,1600",
                        f"--screenshot={shot}", "--virtual-time-budget=3000", page.as_uri()],
                       check=True, capture_output=True, timeout=60)
        image = Image.open(shot).convert("RGB")
    box = ImageChops.difference(image, Image.new("RGB", image.size, "white")).getbbox()
    if box:
        image = image.crop((max(0, box[0] - 24), max(0, box[1] - 24), min(image.width, box[2] + 24),
                            min(image.height, box[3] + 24)))
    image.save(path)
    return image


def phone(image, seed: int):
    """A tilted, slightly blurred, darker JPEG copy."""
    import io
    from PIL import Image, ImageEnhance, ImageFilter

    rng = random.Random(seed)
    out = image.rotate(rng.uniform(-3, 3), resample=Image.BICUBIC, expand=True, fillcolor=(236, 233, 225))
    out = ImageEnhance.Brightness(out.filter(ImageFilter.GaussianBlur(1.1))).enhance(0.9)
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=55)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def similarity(a: str, b: str) -> float:
    return round(difflib.SequenceMatcher(None, lookup.words(a), lookup.words(b)).ratio(), 3)


def run_one(e, image, index, url, model) -> dict:
    turn = session.Turn(session.Source(e.key, image), index, url, model, pace=0)
    start = time.perf_counter()
    try:
        turn.run(lambda event: None)
        error = None
    except Exception as exc:  # noqa: BLE001 - one failed picture is a result, not the end of the run
        error = f"{type(exc).__name__}: {exc}"
    seconds = round(time.perf_counter() - start, 1)
    first = turn.reads[0].problems if turn.reads else []
    read = first[0].markdown if first else ""
    sources = [a["from"] for a in turn.answers]
    return {"exercise": e.key, "reads": len(turn.reads), "seconds": seconds, "error": error,
            "numbers_right": bool(first) and library_match.problem_numbers(read) ==
            library_match.problem_numbers(e.problem_md),
            "similarity": similarity(read, problem_text(e)), "answered_right": f"library:{e.key}" in sources,
            "answered_wrong": [s for s in sources if s.startswith("library:") and s != f"library:{e.key}"],
            "problems_read": len(first), "read": read}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--library", default=os.environ.get("NOTEBOOK_LIBRARY", ""))
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--url", default=ollama.DEFAULT_URL)
    ap.add_argument("--model", default="")
    ap.add_argument("--browser", default="")
    ap.add_argument("--out", default=str(Path.home() / ".csv_plot_studio" / "notebook" / "eval"))
    ap.add_argument("--resume", action="store_true", help="keep the results in --out and do only the rest")
    ap.add_argument("--max", type=int, default=0, help="stop after this many new exercises (0: no limit)")
    args = ap.parse_args(argv)
    if not args.library:
        raise SystemExit("Pass --library (or set NOTEBOOK_LIBRARY) to your solutions file or folder.")
    lib = library.load([args.library])
    index = lookup.Index(lib)
    pool = [e for e in lib.exercises if e.has_problem and e.checker_note]
    sample = random.Random(args.seed).sample(pool, min(args.n, len(pool)))
    found = ollama.models(args.url)
    model = ollama.pick(found, "vision", args.model, avoid="thinking")
    if model is None:
        raise SystemExit(f"No vision model in Ollama. Run: {ollama.PULL_HINT}")
    caps = dict(found)[model]
    browser = find_browser(args.browser)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"{len(sample)} of {len(pool)} exercises with a Problem block and a checker line; model {model} {caps}")
    rows, skipped, done_now = [], [], 0
    saved = out / "eval_notebook.json"
    if args.resume and saved.is_file():
        old = json.loads(saved.read_text(encoding="utf-8"))
        if (old.get("seed"), old.get("n"), old.get("model")) != (args.seed, len(sample), model):
            raise SystemExit("The saved results are for another --seed, --n or model: run without --resume.")
        rows, skipped = old["rows"], old.get("skipped", [])
    done = {r["exercise"] for r in rows} | {s["exercise"] for s in skipped}
    for i, e in enumerate(sample, 1):
        if e.key in done:
            continue
        if args.max and done_now >= args.max:
            break
        done_now += 1
        try:
            clean = draw(browser, problem_text(e), out / f"{e.number}-clean.png")
        except (subprocess.SubprocessError, OSError) as exc:     # the browser, not the Notebook: skip, say so
            skipped.append({"exercise": e.key, "reason": f"{type(exc).__name__}: {exc}"[:300]})
            print(f"{i:3}/{len(sample)} {e.number:>6} skipped: the browser couldn't draw it ({type(exc).__name__})")
            continue
        photo = phone(clean, args.seed + i)
        photo.save(out / f"{e.number}-phone.jpg")
        for kind, image in (("clean", clean), ("phone", photo)):
            row = {"kind": kind, **run_one(e, image, index, args.url, model)}
            rows.append(row)
            mark = "ok " if row["answered_right"] else ("WRONG" if row["answered_wrong"] else "miss")
            print(f"{i:3}/{len(sample)} {e.number:>6} {kind:5} {mark:5} numbers {'ok' if row['numbers_right'] else '--'}"
                  f"  sim {row['similarity']:.2f}  reads {row['reads']}  {row['seconds']:5.1f}s"
                  + (f"  {row['error']}" if row["error"] else ""))
        write_report(out, model, caps, args, sample, rows, skipped)       # after each one: a crash keeps the rest
    summary = write_report(out, model, caps, args, sample, rows, skipped)
    print("\n kind   pictures  numbers right  answered right  answered WRONG  errors  similarity  median s")
    for kind, s in summary.items():
        if s["pictures"]:
            print(f" {kind:5}  {s['pictures']:8}  {s['numbers_right']:13.1%}  {s['answered_right']:14.1%}  "
                  f"{s['answered_wrong']:14}  {s['errors']:6}  {s['mean_similarity']:10.2f}  {s['median_seconds']:8}")
    print(f"\n{len(skipped)} skipped (browser). Wrote {out / 'eval_notebook.json'}")


def write_report(out, model, caps, args, sample, rows, skipped) -> dict:
    def share(kind, key):
        part = [r for r in rows if r["kind"] == kind]
        return round(sum(bool(r[key]) for r in part) / len(part), 3) if part else None

    summary = {kind: {"pictures": sum(r["kind"] == kind for r in rows), "numbers_right": share(kind, "numbers_right"),
                      "answered_right": share(kind, "answered_right"),
                      "answered_wrong": sum(bool(r["answered_wrong"]) for r in rows if r["kind"] == kind),
                      "errors": sum(bool(r["error"]) for r in rows if r["kind"] == kind),
                      "mean_similarity": round(sum(r["similarity"] for r in rows if r["kind"] == kind) /
                                               max(1, sum(r["kind"] == kind for r in rows)), 3),
                      "median_seconds": sorted(r["seconds"] for r in rows if r["kind"] == kind)[
                          sum(r["kind"] == kind for r in rows) // 2] if rows else None}
               for kind in ("clean", "phone")}
    report = {"model": model, "capabilities": list(caps), "library": str(args.library), "n": len(sample),
              "seed": args.seed, "summary": summary, "skipped": skipped, "rows": rows}
    (out / "eval_notebook.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


if __name__ == "__main__":
    main()
