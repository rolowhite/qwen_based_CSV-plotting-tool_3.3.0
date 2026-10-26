"""Reading tables out of PDFs (no tkinter here; pypdfium2 / camelot are imported only when used).

  inspect.py   open a PDF safely (password, damaged, empty, size limit), page kinds (digital / scanned / mixed /
               blank), rendering, page <-> pixel maths
  digital.py   tables from the text layer: camelot's ruling-line and text-position methods, compared
  models.py    the Table / Cell contract the readers return

A digital page is read from its text layer only; a scanned page is rendered and read by the image OCR
(`plotstudio.image_table_extractor`). `plotstudio.pdf_table_extractor` puts the two together for the app.
`inspect` shares its name with a standard-library module: import it through this package.
"""
