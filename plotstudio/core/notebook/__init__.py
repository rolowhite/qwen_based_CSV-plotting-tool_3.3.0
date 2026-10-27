"""Notebook: read a statistics problem from a picture (a local vision model in Ollama) and answer it.

    from plotstudio.core.notebook import library, lookup, session
    index = lookup.Index(library.load(["~/solutions"]))
    turn = session.Turn(session.Source("photo.png", image), index)
    answers = turn.run(print)            # ("status", ...), ("start", None), ("text", ...), ("end", markdown)

For now an answer comes only from the user's own solution library, and only when library_match is sure; the
library files are only read. Live solving (a solver model with a calculator) is the next phase.
"""
