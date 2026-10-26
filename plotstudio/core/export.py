"""Export the pipeline: clean.py, a Jupyter notebook, and a Kaggle submission file.

Every export is written from the same step code the app runs (``Pipeline.code()``), so running
clean.py or the notebook on the training file gives exactly the table the app shows. Values a
step learned (bin edges, kept groups, target means) were learned on the training file and are
written into the code, so a test file is changed the same way: nothing is refitted on test.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from .. import APP_NAME, __version__
from ..codegen import clean_comment, lit
from .pipeline import Pipeline


def read_function(dataset) -> list:
    """`def read(path):` with the same read_csv options and conversions the app used for this file."""
    code = list(getattr(dataset, "load_code", []) or [])
    path = getattr(dataset, "path", None)
    lines = ["def read(path):", '    """Read a CSV the way the app read the training file."""']
    if code and path is not None and code[0].startswith("df = pd.read_csv("):
        first = code[0].replace(lit(Path(path).as_posix()), "path", 1)
        lines.append("    " + first)
        lines += ["    " + ln for ln in code[1:]]
    else:
        lines.append("    df = pd.read_csv(path)")
    lines.append("    return df")
    return lines


def _indent(lines, pad="    ") -> list:
    return [pad + ln if ln.strip() else "" for ln in lines]


def _doc(text) -> str:
    """Text for inside the triple-quoted docstring: one line, and a file name with quotes or backslashes in
    it can neither end the docstring early nor make an invalid escape."""
    return clean_comment(text).replace("\\", "\\\\").replace('"', '\\"')


def clean_script(dataset, pipeline: Pipeline, target: Optional[str] = None) -> str:
    """clean.py: read(), add_features(df, train) and a __main__ that writes <name>_clean.csv."""
    path = Path(getattr(dataset, "path", "data.csv"))
    out_name = f"{path.stem}_clean.csv"
    steps = pipeline.code() or ["# (no steps yet)"]
    lines = [
        f'"""{_doc(path.stem)}: the feature steps accepted in the {APP_NAME} Feature Lab, as plain pandas.',
        "",
        f"Made with {APP_NAME} {__version__}. Run it next to the data:",
        "",
        f"    python {_doc(path.stem)}_clean.py          -> writes {_doc(out_name)}",
        "",
        "Or import it in a notebook:",
        "",
        f"    from {re.sub(r'[^0-9A-Za-z_]', '_', path.stem)}_clean import read, add_features",
        f"    train = add_features(read({_doc(lit(path.name))}), train=True)",
        "    test = add_features(read('test.csv'), train=False)   # what was learned comes from train",
        '"""',
        "import numpy as np",
        "import pandas as pd",
        "",
        "",
    ]
    lines += read_function(dataset)
    lines += ["", "",
              "def add_features(df, train=True):",
              '    """The accepted steps, in order. Bin edges, kept groups and target means were learned on the',
              "    training file and are written in below, so new data (train=False) is changed the same way.",
              '    """',
              "    df = df.copy()"]
    lines += _indent(steps)
    lines += ["    return df", "", "",
              'if __name__ == "__main__":',
              f"    df = add_features(read({lit(path.as_posix())}), train=True)",
              f"    df.to_csv({lit(out_name)}, index=False)",
              f"    print({lit(out_name + ':')}, df.shape[0], 'rows,', df.shape[1], 'columns')",
              ""]
    return "\n".join(lines)


def _cell(kind: str, text: str) -> dict:
    lines = text.split("\n")
    source = [ln + "\n" for ln in lines[:-1]] + [lines[-1]]
    cell = {"cell_type": kind, "metadata": {}, "source": source}
    if kind == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


def notebook(dataset, pipeline: Pipeline, target: Optional[str] = None, evaluation=None) -> dict:
    """A Jupyter notebook (nbformat 4) that reads the file and runs every step, one cell each."""
    path = Path(getattr(dataset, "path", "data.csv"))
    cells = [_cell("markdown", f"# Feature engineering for {path.name}\n\n"
                               f"Made with {APP_NAME} {__version__}: every step you accepted in the Feature Lab, "
                               "one cell each. Run the cells from the top. `train = True` means *this is the training "
                               "file*: target encodings are then computed out-of-fold. Values a step learned "
                               "(bin edges, kept groups, target means) come from the training file and are written "
                               "in the code, so a test file is changed the same way.")]
    cells.append(_cell("code", "import numpy as np\nimport pandas as pd"))
    cells.append(_cell("code", "\n".join(read_function(dataset)) +
                       f"\n\n\ndf = read({lit(path.as_posix())})\ntrain = True\ndf.shape"))
    for i, step in enumerate(pipeline.steps, 1):
        cells.append(_cell("markdown", f"## {i}. `{step.name}`: {step.label}"))
        cells.append(_cell("code", "\n".join(step.code())))
    tail = "df.head()" if not pipeline.outputs else f"df[{lit(pipeline.outputs[:12])}].head(10)"
    cells.append(_cell("code", tail))
    if evaluation is not None and getattr(evaluation, "scores", None):
        rows = "\n".join(f"| {s.name} | {s.before_mean:.3f} ± {s.before_std:.3f} | {s.after_mean:.3f} ± "
                         f"{s.after_std:.3f} | {s.gain:+.3f}{'' if s.significant else ' (not significant)'} |"
                         for s in evaluation.scores)
        cells.append(_cell("markdown", f"## 5-fold cross-validation ({evaluation.metric})\n\n"
                                       "| model | without the new features | with them | gain |\n|---|---|---|---|\n"
                                       + rows))
    if target:
        cells.append(_cell("markdown", "## New data (e.g. Kaggle's test.csv)\n\nThe same steps with "
                                       "`train = False`: nothing is learned again."))
        steps = "\n".join(_indent(pipeline.code()))
        cells.append(_cell("code", "def add_features(df, train=True):\n    df = df.copy()\n" + steps +
                           "\n    return df\n\n\n# test = add_features(read('test.csv'), train=False)"))
    return {"cells": cells,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 4}


def notebook_json(dataset, pipeline: Pipeline, target: Optional[str] = None, evaluation=None) -> str:
    return json.dumps(notebook(dataset, pipeline, target, evaluation), indent=1, ensure_ascii=False)


def notebook_code(nb: dict) -> str:
    """All code cells of a notebook joined (to run it without Jupyter, e.g. in tests)."""
    return "\n\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")


def guess_id_column(test: pd.DataFrame, train_columns) -> Optional[str]:
    """The column that identifies the rows of a test file (PassengerId, id ...), if there is one."""
    from ..data import ID_NAMES
    for c in test.columns:
        if ID_NAMES.search(str(c)) and test[c].is_unique:
            return c
    for c in test.columns:
        if test[c].is_unique and pd.api.types.is_integer_dtype(test[c]):
            return c
    return None


def submission(train: pd.DataFrame, test: pd.DataFrame, pipeline: Pipeline, target: str, id_column: str, *,
               base_columns=None, model: str = "boosting", infos: Optional[dict] = None) -> pd.DataFrame:
    """A Kaggle submission: the pipeline applied to test (nothing refitted), a baseline model trained
    on all of train (base columns + accepted features), and one prediction per test row.

    train  the training table AFTER the pipeline (the app's working table)
    test   the raw test table (as read from the file)
    """
    from .evaluate import EvaluateError, fit_and_predict
    if id_column not in test.columns:
        raise EvaluateError(f"The test file has no column '{id_column}'.")
    test_t = pipeline.transform(test, train=False)
    new = [c for c in pipeline.outputs if c in train.columns]
    if base_columns is None:
        base_columns = [c for c in train.columns if c not in set(new)]
    columns = [c for c in base_columns if c not in (target, id_column)] + new
    left_out = [c for c in columns if c not in test_t.columns]      # only in train: the model can't use them
    columns = [c for c in columns if c in test_t.columns]
    pred = fit_and_predict(train, test_t, target, columns, model=model, infos=infos)
    out = pd.DataFrame({id_column: test[id_column].to_numpy(), target: pred.to_numpy()})
    out.attrs["left_out"] = left_out                                 # said in the app's message
    if pd.api.types.is_bool_dtype(train[target]) or set(pd.unique(train[target].dropna())) <= {0, 1}:
        try:
            out[target] = out[target].astype(int)
        except (TypeError, ValueError):
            pass
    return out
