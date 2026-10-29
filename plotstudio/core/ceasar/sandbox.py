"""Run pandas code on a copy of a table: checked first, then executed with a short list of names and a time limit.

The code comes from a starter task or from the local model, which has read cell values of the user's file: a cell
that says "ignore your instructions and ..." must not be able to do harm. So the code may only use `df`, `pd`,
`np`, `re` and `math`, no imports, no files or network, no names that start with an underscore, no `while` loops or
function definitions (a `lambda` is fine), and it is stopped after TIMEOUT seconds. This is a guard for a tool that runs
on the user's own computer, not a boundary against someone who can run code there anyway.

The code leaves its result in `df` (the changed table) and/or `answer` (what a question asks for).
"""
from __future__ import annotations

import ast
import builtins as _b
import contextlib
import io
import math
import re
import sys
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

MAX_CODE = 6000
TIMEOUT = 30.0
MAX_OUTPUT = 4000

BAD_NAMES = {"open", "exec", "eval", "compile", "input", "getattr", "setattr", "delattr", "globals", "locals", "vars",
             "dir", "breakpoint", "memoryview", "help", "exit", "quit", "os", "sys", "subprocess", "importlib",
             "builtins", "socket", "shutil", "pathlib"}
# attribute names: no writing or reading files, no evaluating strings, no reaching into modules
BAD_ATTRS = {"to_csv", "to_pickle", "to_excel", "to_sql", "to_parquet", "to_json", "to_feather", "to_hdf",
             "to_clipboard", "to_stata", "to_xml", "to_latex", "to_html", "to_orc", "to_gbq", "to_markdown",
             "eval", "load", "save", "savez", "savez_compressed", "savetxt", "loadtxt", "genfromtxt", "fromfile",
             "tofile", "memmap", "ctypeslib", "lib", "f2py", "distutils", "testing", "io", "compat", "os", "sys",
             "subprocess", "builtins", "format_map", "system", "popen", "importlib", "api_extension", "plotting",
             "style", "read_clipboard", "to_string", "ExcelWriter", "HDFStore", "ExcelFile", "dump", "tofile"}
BAD_NODES = (ast.Import, ast.ImportFrom, ast.While, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Global,
             ast.Nonlocal, ast.With, ast.AsyncWith, ast.Await, ast.Yield, ast.YieldFrom, ast.AsyncFor)
SAFE_BUILTINS = {name: getattr(_b, name) for name in (
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "int", "isinstance", "len", "list",
    "map", "max", "min", "pow", "print", "range", "repr", "reversed", "round", "set", "slice", "sorted", "str", "sum",
    "tuple", "zip", "Exception", "ValueError", "KeyError", "TypeError", "IndexError", "ZeroDivisionError")}


class CodeRefused(ValueError):
    """The code uses something it may not (the message says what)."""


class CodeFailed(RuntimeError):
    """The code was allowed but raised an error or ran too long (the message says what to fix)."""


@dataclass
class Run:
    df: pd.DataFrame
    answer: Any = None
    output: str = ""
    seconds: float = 0.0


def check(code: str) -> ast.Module:
    """The parsed code, or CodeRefused with the reason."""
    if not isinstance(code, str) or not code.strip():
        raise CodeRefused("there is no code")
    if len(code) > MAX_CODE:
        raise CodeRefused(f"the code is longer than {MAX_CODE} characters")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise CodeRefused(f"the code is not valid Python ({exc.msg}, line {exc.lineno})") from exc
    for node in ast.walk(tree):
        if isinstance(node, BAD_NODES):
            raise CodeRefused(f"{type(node).__name__} is not allowed here")
        if isinstance(node, ast.Name) and (node.id in BAD_NAMES or node.id.startswith("_")):
            raise CodeRefused(f"the name '{node.id}' is not allowed")
        if isinstance(node, ast.Attribute) and (node.attr in BAD_ATTRS or node.attr.startswith("_")
                                                or node.attr.startswith("read_")):
            raise CodeRefused(f"'.{node.attr}' is not allowed (no files, no evaluating text)")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
            raise CodeRefused("text containing '__' is not allowed")
    return tree


def _tracer(deadline: float):
    def local(frame, event, arg):
        if time.monotonic() > deadline:
            raise TimeoutError
        return local

    def start(frame, event, arg):
        return local if frame.f_code.co_filename == "<ceasar>" else None     # only the user's own lines
    return start


def run(df: pd.DataFrame, code: str, timeout: float = TIMEOUT) -> Run:
    """Run `code` on a copy of `df`. Returns the changed table (and `answer`); the original is never touched."""
    tree = check(code)
    namespace = {"__builtins__": SAFE_BUILTINS, "df": df.copy(), "pd": pd, "np": np, "re": re, "math": math,
                 "answer": None}
    out = io.StringIO()
    started = time.monotonic()
    previous = sys.gettrace()
    sys.settrace(_tracer(started + timeout))
    try:
        with contextlib.redirect_stdout(out):
            exec(compile(tree, "<ceasar>", "exec"), namespace)      # noqa: S102 - checked above
    except TimeoutError:
        raise CodeFailed(f"it ran longer than {timeout:.0f} seconds") from None
    except Exception as exc:  # noqa: BLE001 - whatever the code did wrong, the model gets told
        raise CodeFailed(f"{type(exc).__name__}: {exc}") from exc
    finally:
        sys.settrace(previous)
    result = namespace.get("df")
    if not isinstance(result, pd.DataFrame):
        raise CodeFailed("`df` must still be a table (DataFrame) at the end")
    if result.shape[1] == 0:
        raise CodeFailed("the result has no columns left")
    return Run(result, namespace.get("answer"), out.getvalue()[:MAX_OUTPUT], round(time.monotonic() - started, 2))
