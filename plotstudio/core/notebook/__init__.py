"""Notebook: find a statistics problem in the user's own solution library and show the stored solution.

    from plotstudio.core.notebook import library, lookup
    lib = library.load(["~/solutions"], cache_path=Path("~/.csv_plot_studio/notebook_index.json"))
    result = lookup.Index(lib).lookup("A box contains 4 red and 3 black balls ...")
    result.status, result.best.exercise.number

The library files are only read. LLMs never compute anything here (live solving is a later phase).
"""
