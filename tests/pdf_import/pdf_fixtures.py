"""Small PDFs with known tables, made with reportlab when the tests run. The ground truth is the lists below, so
accuracy is measured without anyone typing tables in. Fonts: the app's own IBM Plex (it has the Unicode minus
and dashes), so the files come out the same on every machine."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

FONTS = Path(__file__).resolve().parents[2] / "plotstudio" / "assets" / "fonts"

HEADER = ["Region", "Units", "Revenue", "Change"]
ROWS = [["North", "1,204", "45,310.50", "(1,250)"],
        ["South", "987", "38,002.10", "4.5%"],
        ["East", "1,530", "61,447.00", "−320"],          # a Unicode minus
        ["West", "640", "21,900.75", "12.3*"],
        ["Total", "4,361", "166,660.35", "—"]]           # an em dash for "nothing"
TRUTH = [HEADER] + ROWS
WIDE = [["Item"] + [f"Q{i}" for i in range(1, 11)]] + [[f"item {r}"] + [str((r + 1) * (c + 3)) for c in range(10)]
                                                       for r in range(6)]
MERGED = [["Region", "Revenue", "", "Notes"], ["", "2023", "2024", ""],
          ["North", "1,000", "1,100", "steady"],
          ["South", "900", "950", "new store opened in the second half"],
          ["East", "1,200", "1,150", "-"]]
MERGED_COLUMNS = ["Region", "Revenue_2023", "Revenue_2024", "Notes"]
STAFF = [["Office", "Staff", "Share"], ["Leeds", "42", "31.8%"], ["York", "57", "43.2%"], ["Hull", "33", "25.0%"]]
PROSE = ("Sales rose in every region but the east, where a store closed for refurbishment in the spring. "
         "The figures below are unaudited and may change when the year-end accounts are signed off. ")
LAYOUT: Dict[str, dict] = {}       # where some tables were drawn (PDF points), for the marked-area tests
COL_MM = [35, 25, 35, 25]


def _fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont("Plex", str(FONTS / "IBMPlexSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Plex-SemiBold", str(FONTS / "IBMPlexSans-SemiBold.ttf")))


def _styles():
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("FONT", (0, 0), (-1, -1), "Plex", 10),
                       ("FONT", (0, 0), (-1, 0), "Plex-SemiBold", 10), ("ALIGN", (1, 1), (-1, -1), "RIGHT")])
    plain = TableStyle([("FONT", (0, 0), (-1, -1), "Plex", 10), ("FONT", (0, 0), (-1, 0), "Plex-SemiBold", 10),
                        ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black)])
    return grid, plain


def _zero_pages() -> bytes:
    """A well-formed PDF whose page tree is empty."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [] /Count 0 >>"]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def build(out: Path) -> Dict[str, Path]:
    """Writes every fixture into `out` and returns {name: path}."""
    import pypdfium2 as pdfium
    from reportlab.lib import pdfencrypt
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    _fonts()
    grid, plain = _styles()
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontName = "Plex"
    heading = styles["Heading3"]
    heading.fontName = "Plex-SemiBold"
    paths: Dict[str, Path] = {}
    W, H = A4

    def doc(name, story, pagesize=A4, **kw):
        paths[name] = out / f"{name}.pdf"
        SimpleDocTemplate(str(paths[name]), pagesize=pagesize, leftMargin=20 * mm, rightMargin=20 * mm,
                          **kw).build(story)

    widths = [w * mm for w in COL_MM]
    doc("bordered", [Paragraph("Table 1. Sales by region", heading), Table(TRUTH, style=grid)])
    doc("borderless", [Paragraph("Table 2. Sales by region", heading), Table(TRUTH, style=plain, colWidths=widths)])
    doc("both", [Paragraph("Table 1. With borders", heading), Table(TRUTH, style=grid), Spacer(1, 20 * mm),
                 Paragraph("Table 2. Without borders", heading), Table(TRUTH, style=plain, colWidths=widths)])
    merged_style = TableStyle(list(grid.getCommands()) + [("SPAN", (1, 0), (2, 0)), ("SPAN", (0, 0), (0, 1)),
                                                          ("SPAN", (3, 0), (3, 1)),
                                                          ("FONT", (0, 0), (-1, 1), "Plex-SemiBold", 10)])
    rows = [r[:] for r in MERGED]
    rows[3][3] = Paragraph(MERGED[3][3], body)                  # wraps onto two lines in its cell
    doc("merged", [Table(rows, style=merged_style, colWidths=[30 * mm, 25 * mm, 25 * mm, 40 * mm])])
    doc("landscape", [Table(WIDE, style=grid)], pagesize=landscape(A4))
    doc("report", [Paragraph("Quarterly report", styles["Heading1"]), Paragraph(PROSE * 3, body),
                   Paragraph("Table 1. Sales by region", heading), Table(TRUTH, style=grid), Spacer(1, 6 * mm),
                   Paragraph(PROSE * 2, body), Paragraph("Table 2. Staff by office", heading),
                   Table(STAFF, style=plain, colWidths=[35 * mm, 25 * mm, 25 * mm]), Spacer(1, 6 * mm),
                   Paragraph("* provisional figures", body)])

    # three kinds of rotated page, each holding WIDE
    def rotated(name, box, rotate, turn_content):
        paths[name] = out / f"{name}.pdf"
        c = canvas.Canvas(str(paths[name]), pagesize=box)
        if rotate:
            c.setPageRotation(rotate)
        t = Table(WIDE, style=grid)
        t.wrapOn(c, 260 * mm, 180 * mm)
        if turn_content:                                         # the content itself runs bottom to top
            c.saveState()
            c.translate(box[0], 0)
            c.rotate(90)
            t.drawOn(c, 20 * mm, 100 * mm)
            c.restoreState()
        else:
            t.drawOn(c, 20 * mm, 120 * mm)
        c.showPage()
        c.save()

    rotated("rotated", landscape(A4), 90, False)       # upright content on a page carrying /Rotate 90: shown sideways
    rotated("rot_lscape", A4, 90, True)                # sideways content turned back by /Rotate 90: shown upright
    rotated("rot_sideways", A4, 0, True)               # sideways content, no /Rotate (a "sidewaystable")

    # a borderless table drawn at a known place, for marking it by hand
    paths["placed"] = out / "placed.pdf"
    c = canvas.Canvas(str(paths["placed"]), pagesize=A4)
    t = Table(TRUTH, style=plain, colWidths=widths)
    _, th = t.wrapOn(c, W, H)
    x0, y0 = 120.0, 500.0
    t.drawOn(c, x0, y0)
    edges = [x0]
    for w in widths:
        edges.append(edges[-1] + w)
    LAYOUT["placed"] = {"left": x0, "right": edges[-1], "bottom": y0, "top": y0 + th, "dividers": edges[1:-1]}
    c.showPage()
    c.save()

    # a small sideways table on a page of upright text: camelot reads the page upright, so the table can't be
    paths["minority"] = out / "minority.pdf"
    c = canvas.Canvas(str(paths["minority"]), pagesize=A4)
    text = c.beginText(20 * mm, H - 20 * mm)
    text.setFont("Plex", 10)
    for i in range(48):
        text.textLine(f"Line {i + 1}: {PROSE[:60]}")
    c.drawText(text)
    c.saveState()
    c.translate(W - 20 * mm, 30 * mm)
    c.rotate(90)
    small = Table(STAFF, style=grid)
    small.wrapOn(c, W, H)
    small.drawOn(c, 0, 0)
    c.restoreState()
    c.showPage()
    c.save()

    # password protected (user password "secret"); copying forbidden unless opened with the owner password
    doc("encrypted", [Table(TRUTH, style=grid)], encrypt=pdfencrypt.StandardEncryption("secret", canPrint=1))
    doc("nocopy", [Table(TRUTH, style=grid)],
        encrypt=pdfencrypt.StandardEncryption("", ownerPassword="owner", canPrint=1, canCopy=0))

    # pictures of pages
    page = pdfium.PdfDocument(str(paths["bordered"]))[0]
    picture = page.render(scale=100 / 72).to_pil().convert("RGB")
    page.close()

    def canvas_pdf(name):
        paths[name] = out / f"{name}.pdf"
        return canvas.Canvas(str(paths[name]), pagesize=A4)

    c = canvas_pdf("scanned")
    c.drawImage(ImageReader(picture), 0, 0, width=W, height=H)
    c.showPage()
    c.save()
    c = canvas_pdf("searchable")                    # a scan with an invisible OCR text layer on top
    c.drawImage(ImageReader(picture), 0, 0, width=W, height=H)
    text = c.beginText(72, 700)
    text.setTextRenderMode(3)
    text.setFont("Helvetica", 10)
    for line in ["Region Units Revenue Change", "North 1,204 45,310.50 (1,250)", "South 987 38,002.10 4.5%"]:
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    c = canvas_pdf("mixed")                          # text and a picture covering about a quarter of the page
    text = c.beginText(20 * mm, H - 25 * mm)
    text.setFont("Plex", 10)
    for i in range(12):
        text.textLine(PROSE[:90])
    c.drawText(text)
    c.drawImage(ImageReader(picture), 20 * mm, 60 * mm, width=W / 2, height=H / 2)
    c.showPage()
    c.save()
    c = canvas_pdf("nested")                         # a full-page picture inside a form XObject, scaled into place
    c.beginForm("scan")
    c.drawImage(ImageReader(picture), 0, 0, width=100, height=100)
    c.endForm()
    c.saveState()
    c.scale(W / 100, H / 100)
    c.doForm("scan")
    c.restoreState()
    c.showPage()
    c.save()
    c = canvas_pdf("drawn")                          # no text at all, only shapes (like text turned into outlines)
    for i in range(260):
        c.line(50 + (i % 26) * 18, 100 + (i // 26) * 50, 60 + (i % 26) * 18, 130 + (i // 26) * 50)
    c.showPage()
    c.save()
    c = canvas_pdf("blank")
    c.showPage()
    c.save()
    c = canvas_pdf("mixed_pages")                    # page 1 digital, page 2 scanned
    c.setFont("Plex", 11)
    c.drawString(72, H - 72, "Page one has a text layer and a short note.")
    c.showPage()
    c.drawImage(ImageReader(picture), 0, 0, width=W, height=H)
    c.showPage()
    c.save()

    # a cropped page: the crop box doesn't start at the media box's corner
    paths["cropped"] = out / "cropped.pdf"
    src = pdfium.PdfDocument(str(paths["bordered"]))
    pg = src[0]
    pg.set_cropbox(40, 300, 520, 800)
    pg.close()
    src.save(str(paths["cropped"]))
    src.close()

    # 500 pages, each with a little table (lazy loading and memory)
    c = canvas_pdf("pages500")
    for p in range(500):
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, 280 * mm, f"Page {p + 1}")
        t = Table([["a", "b"], [str(p), str(p * 2)]], style=TableStyle([("GRID", (0, 0), (-1, -1), 0.6,
                                                                         colors.black)]))
        t.wrapOn(c, 100 * mm, 50 * mm)
        t.drawOn(c, 20 * mm, 250 * mm)
        c.showPage()
    c.save()

    # broken files
    data = paths["bordered"].read_bytes()
    paths["corrupt"] = out / "corrupt.pdf"
    paths["corrupt"].write_bytes(data[: len(data) // 2])
    paths["empty"] = out / "empty.pdf"
    paths["empty"].write_bytes(b"")
    paths["nopages"] = out / "nopages.pdf"
    paths["nopages"].write_bytes(_zero_pages())
    paths["text_file"] = out / "notes.pdf"
    paths["text_file"].write_text("These are notes, not a PDF.\n", encoding="utf-8")
    return paths
