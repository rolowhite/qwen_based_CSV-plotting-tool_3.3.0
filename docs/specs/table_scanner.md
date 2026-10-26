# Prompt: Table Scanner for CSV Plot Studio (for Claude Code)

> Paste everything below the line into Claude Code, opened in the CSV Plot Studio repo.
> One phase per session. Claude Code stops after each phase for your review.

---

## Your role and the goal
You are a senior Python engineer adding a **Table Scanner** to my desktop app **CSV Plot Studio** (Python 3.10+, Tkinter, pandas, matplotlib/seaborn; existing features include EDA Analyze, Plot Suggestions, Cleaning Pipeline, Stats Solver).

**Goal:** I photograph printed table pages with my phone. The photos reach the desktop app over my local Wi-Fi via a QR code. The app turns them into **one verified pandas DataFrame**, saves it as CSV/XLSX, and opens it in the existing EDA tools.

**Why accuracy beats speed here:** one misread digit silently corrupts every later analysis, and the user won't notice. So every design choice should make errors *visible*: flag them, cross-check them, and never hide uncertainty.

## Environment
- My PC: Linux Mint and Windows (dual boot), RTX 4060 Ti, 16 GB RAM. The code must run on both OSes.
- Local AI runs through **Ollama** (`http://localhost:11434`). The vision model name is a **setting**; don't hard-code one. Check what's installed via `GET /api/tags` and tell me in the UI if no vision-capable model is present.
- Everything must work **offline on the LAN**. No cloud services and no API keys.

## Step 0: before writing any code
1. Read the repo. Summarise the app entry point, how tabs are built, the `core/` package layout, how a DataFrame is loaded into the app, the `Pipeline`/step system, and whether a phone-upload module already exists (Snap & Solve may have one).
2. Propose a file plan for **Phase 1 only**, plus any new dependencies.
3. **Stop and wait for my approval.**

## Hard rules (apply to every phase)
- `core/` never imports tkinter. UI code only renders results from `core/`.
- Long work (server, OCR, model calls) runs in background threads. The UI talks to them only through a `queue.Queue` that Tkinter checks with `after()`. Tkinter isn't thread-safe, so touching widgets from a worker thread causes random crashes.
- Never use `eval`/`exec` on any text from OCR, models or the phone.
- An AI model may **read** cells, but it never **decides** that a value is correct. Validation is done by code (Phase 3).
- No hard-coded column names or dataset-specific logic.
- Never claim a model, library or setting behaves a certain way without checking it in code or docs. If unsure, write a small probe and report the result.
- Run the full existing test suite every phase. Existing features must keep working.

## Architecture
```
core/
  phone_bridge/        # shared with Snap & Solve. Reuse it if it exists; refactor into this if not
    server.py          # FastAPI app, token, upload endpoint, static page
    page.html          # mobile upload page
    network.py         # LAN IP detection, port selection
  table_scanner/
    models.py          # dataclasses: ScanJob, Page, TableRegion, Cell, Table, Issue
    preprocess.py      # image cleanup
    detect.py          # find table regions on a page
    extract_vlm.py     # Ollama vision model → cells
    extract_ocr.py     # PaddleOCR table structure / img2table → cells
    reconcile.py       # merge the two extractions, cell-level agreement
    stitch.py          # multi-page join, header dedupe
    validate.py        # types, shapes, totals → list[Issue]
    export.py          # CSV/XLSX + provenance sidecar JSON
ui/
  table_scanner_tab.py # QR dialog, page strip, review grid
tests/table_scanner/ + tests/phone_bridge/
```
Every extractor returns the **same** `Table` dataclass:
`Table(cells: list[Cell], n_rows, n_cols, header_rows, source_page, bbox)` and
`Cell(row, col, text, confidence: float | None, bbox_on_image, source: "vlm" | "ocr" | "both" | "user")`.
Keeping one contract means extractors can be swapped, compared and tested in isolation.

## Phases

### Phase 1: Phone bridge + single printed page → CSV, with review
**Phone bridge**
- "Scan from phone" button → start a FastAPI server (uvicorn, background thread) on `0.0.0.0` at the first free port from 8765 up.
- Detect the LAN IP (UDP-socket trick, with a fallback that lists all interfaces and lets me pick if several exist). Generate a one-time token (`secrets.token_urlsafe(16)`). Show a QR code (`qrcode` library) for `http://<ip>:<port>/u?t=<token>`, the plain URL underneath, and a "Copy URL" button.
- `GET /u` serves `page.html`: big "Take photo" button using `<input type="file" accept="image/*" capture="environment" multiple>`, page thumbnails with reorder/delete, a **client-side resize to a max 2000 px long side** (canvas → JPEG quality 0.9) before upload, a per-file progress bar, and a "✓ N pages received" confirmation. Plain HTML/JS, no build step and no external CDN, because the phone may have no internet.
- `POST /upload?t=` accepts multipart images. Reject a wrong or expired token (403), files over 15 MB, and non-image content (check magic bytes with Pillow, not just the extension). Save to `<app_data>/inbox/<job_id>/page_###.jpg` with EXIF orientation applied. Put a message on the queue.
- The server stops when the dialog closes or after 10 minutes idle; the token dies with it. Show a status line in the app: "Waiting for phone…", "3 pages received".
- Fallbacks in the same dialog: "Open image files…" and "Open PDF…" (render pages with PyMuPDF).
- Troubleshooting panel (collapsible): same Wi-Fi required, use the phone hotspot if the network isolates devices, and the exact firewall command per OS (`sudo ufw allow <port>/tcp` on Linux; Windows prompt).

**Extraction (single page, single table)**
- `preprocess.py`: EXIF fix, page-edge detection + perspective correction (OpenCV), deskew, shadow removal / CLAHE, grayscale copy for OCR. A **blur check** (variance of Laplacian): below the threshold, warn "Photo too blurry, retake?" with an override.
- `extract_vlm.py`: send the cleaned image to the configured Ollama vision model. Ask for **JSON only** (`{"header_rows": n, "rows": [[...], ...]}`) using Ollama's structured-output `format` schema. The instruction says: transcribe exactly, keep empty cells as `""`, don't compute or correct anything, and keep the original number formatting. Timeout 120 s, cancellable.
- Build the `Table`, then a DataFrame (header from `header_rows`; multi-row headers flattened as `Parent_Child`).

**Review grid (the most important UI)**
- Left: the page image (zoom/pan). Right: an editable grid (`ttk.Treeview` with in-place editing, or `tksheet` if you judge it better; justify the choice).
- Clicking a cell **highlights its bbox on the image**, and clicking on the image selects the cell. If the VLM gives no bboxes, highlight the row band estimated from the row position and say so.
- Edits mark the cell `source="user"`. Undo/redo for edits.
- Buttons: "Accept → open in EDA", "Export CSV", "Export XLSX".

**Done when:** a clear phone photo of a printed table (~10×6) goes from phone to an exported CSV through the review grid; the tests below pass; and the QR flow works with the phone on the same Wi-Fi, on Linux.

### Phase 2: Multi-page, multi-table
- `detect.py`: find table regions per page (img2table or line/contour detection; pick one, explain why, and keep it swappable). If a page has several tables, show them as separate selectable regions; I choose which to keep.
- `stitch.py`: join pages in the order shown on the page strip.
  - Detect repeated headers on later pages (fuzzy match ≥ 0.9 normalised text) and drop them.
  - If the column count differs between pages, **don't guess**: show a column-mapping dialog.
  - Handle "continued" tables where page 2 has no header.
  - Add an optional `_source_page` column (on by default, removable).
- Process pages concurrently (max 2 workers, because of VRAM) with per-page progress, and show results as each page finishes.
- **Done when:** a 3-page table with headers repeated on each page becomes one DataFrame with no duplicate header rows and the correct row count.

### Phase 3: Automatic validation
`validate.py` returns `list[Issue(severity, row, col, message, suggestion)]`. Show issues as cell colours (🔴 error, 🟡 check) plus an issues list where clicking an issue jumps to the cell.
- **Column type inference:** if ≥ 80% of a column parses as numeric, flag the cells that don't. Suggest fixes for common OCR confusions (`O→0`, `l/I→1`, `S→5`, `B→8`), comma vs dot decimals, thousands separators, a stray `%`/currency sign. Suggestions are applied **only when I accept them**, one at a time or "accept all of this type".
- **Shape checks:** ragged rows, completely empty rows or columns, and a header that looks like data.
- **Totals check:** detect "Total/Sum/Grand total" rows or columns (case-insensitive, configurable keywords) and recompute them. A mismatch → 🔴 on the total and 🟡 on every cell in that row or column, with the expected vs found difference. If the difference equals a single-digit change in one cell, point to the likely cell.
- **Range/outlier hint:** a value more than 10× the column median → 🟡 (a possible missing decimal point).
- Export is allowed with unresolved 🟡 issues but needs a confirmation if any 🔴 remains.
- **Done when:** on a test table with planted errors (an O in a number, a wrong total, a missing decimal), every planted error is flagged and no clean cell is flagged 🔴.

### Phase 4: Dual-engine cross-check
- `extract_ocr.py`: a second, independent extraction with PaddleOCR table-structure recognition (or img2table + an OCR backend). It must run on CPU if there's no GPU build, and install as an optional extra. The rest of the app must still work if it's missing.
- `reconcile.py`: align the two tables (same shape → cell-by-cell; different shape → align rows by text similarity, then columns). For each cell: values agree after normalisation → `source="both"`, high trust; they disagree → keep the VLM value, mark 🟡, and show both options in a cell dropdown; only one engine read it → mark 🟡.
- A summary banner: "92% of cells confirmed by both engines, 14 cells need checking."
- **Done when:** on the test set, cells where the engines agree are correct ≥ 99% of the time (report the measured number), and every planted error is either flagged or caught by disagreement.

### Phase 5: Handwritten tables (experimental)
- A "Handwritten" toggle: a VLM-only path (PaddleOCR is weak on handwriting), validation thresholds relaxed, and **every** numeric cell marked for review by default.
- Report the measured accuracy honestly in the summary. Don't overstate it.

## Export and integration
- `export.py`: CSV (UTF-8 with BOM option for Excel), XLSX (openpyxl; flagged cells keep a yellow fill and a comment with the issue), and a sidecar `<name>.scan.json`. The sidecar holds the source image paths, page order, engines and model names used, the time, every user edit (old → new) and the unresolved issues. It records where the numbers came from.
- "Accept → open in EDA" loads the DataFrame through the app's **existing** load path, so EDA Analyze, Plot Suggestions, the Cleaning Pipeline and the Stats Solver work unchanged. Record the scan as the first step in the `Pipeline` (`{"op": "scan_import", "sidecar": ...}`) so exported notebooks state where the data came from.

## Settings (persisted)
Ollama URL, vision model name, server port start, upload size limit, blur threshold, totals keywords, max workers, keep or delete inbox images after export (default: keep 7 days).

## Tests (pytest)
- **phone_bridge:** the token is required (403 without it); oversized and non-image uploads are rejected; a valid upload lands in the inbox and posts a queue message; the server shuts down cleanly. Use FastAPI `TestClient`, not a real phone.
- **preprocess:** a synthetically rotated/skewed table image comes out upright (angle error < 2°); the blur check flags a Gaussian-blurred image.
- **Synthetic fixtures:** write a generator that renders DataFrames to table images with Pillow (varied fonts, grid/no-grid, noise, rotation). Ground truth is then known exactly, so you can measure accuracy without me.
- **validate / stitch / reconcile:** unit tests with hand-built `Table` objects covering every rule, including the planted-error cases above and "no false 🔴 on clean data".
- **Real photos:** create `tests/table_scanner/real/` with a README that says what I should add (10+ phone photos of printed tables with a ground-truth CSV each). Tests skip if empty. **Don't invent ground truth.**
- **Evaluation script** `scripts/eval_table_scanner.py`: cell accuracy, numeric-cell accuracy, row/column shape accuracy, error-flag recall and the false-flag rate, per engine and after reconcile. Print a table and save JSON.
- Model-dependent tests are marked `@pytest.mark.ollama` and skipped when Ollama isn't reachable.

## Output format for each phase
1. Plan (files, dependencies) → **wait for approval**
2. Implementation
3. Test run output (and evaluation numbers from Phase 3 on)
4. Summary: what changed, how to try it (exact steps), known limitations, and what you recommend for the next phase

## Out of scope (don't build)
Cloud OCR, user accounts, internet tunnelling for the phone, a native mobile app, HTTPS/live camera preview in the browser, automatic acceptance of fixes without my confirmation.

Start with **Step 0**.
