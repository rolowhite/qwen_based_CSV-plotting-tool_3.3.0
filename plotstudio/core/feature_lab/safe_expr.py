"""Your own feature from a formula, checked piece by piece. Nothing you type is run with eval.

    Fare / (SibSp + Parch + 1)
    log1p(Fare) * (Age < 18)
    where(isna(Age), 1, 0)
    `Flight Distance` / 1000          (backticks for names with spaces)

How it stays safe: the formula is parsed with Python's ast module (parsing runs nothing),
every piece is checked against a short allow-list (column names, numbers, + - * / // % **,
comparisons, and / or / not, and the functions below), and the pandas code is then WRITTEN
from the checked pieces only. Attribute access (x.y), indexing, imports, lambdas, names like
__import__ and any other function are refused with a message saying what is allowed.
"""
from __future__ import annotations

import ast
import difflib
import keyword
import re

from ...codegen import lit

MAX_LENGTH = 500
MAX_NODES = 300

# name -> (code, how many arguments, what it does)
FUNCTIONS = {
    "log": ("np.log", 1, "natural log"),
    "log1p": ("np.log1p", 1, "log(1 + x), fine with zeros"),
    "log10": ("np.log10", 1, "log base 10"),
    "log2": ("np.log2", 1, "log base 2"),
    "exp": ("np.exp", 1, "e to the power x"),
    "sqrt": ("np.sqrt", 1, "square root"),
    "abs": ("np.abs", 1, "size without the sign"),
    "floor": ("np.floor", 1, "round down"),
    "ceil": ("np.ceil", 1, "round up"),
    "round": ("np.round", (1, 2), "round(x) or round(x, decimals)"),
    "minimum": ("np.minimum", 2, "the smaller of two"),
    "maximum": ("np.maximum", 2, "the larger of two"),
    "clip": ("np.clip", 3, "clip(x, low, high)"),
    "where": ("np.where", 3, "where(condition, if_true, if_false)"),
    "isna": ("pd.isna", 1, "True where the value is missing"),
    "notna": ("pd.notna", 1, "True where the value is there"),
}
CONSTANTS = {"pi": "np.pi", "e": "np.e"}
BIN_OPS = {ast.Add: ("+", 5), ast.Sub: ("-", 5), ast.Mult: ("*", 6), ast.Div: ("/", 6), ast.FloorDiv: ("//", 6),
           ast.Mod: ("%", 6), ast.Pow: ("**", 8)}
COMPARE = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
ATOM = 9


class ExprError(ValueError):
    """A formula that can't be used (the message says why and what to write instead)."""


def allowed_help() -> str:
    funcs = ", ".join(f"{name}()" for name in FUNCTIONS)
    return f"Use column names, numbers, + - * / // % **, < <= > >= == !=, and / or / not, and {funcs}."


def _backticks(text: str, columns) -> tuple:
    """`Some Name` -> a placeholder word, so names with spaces can be written."""
    names = {}

    def swap(match):
        name = match.group(1)
        if name not in columns:
            raise ExprError(f"`{name}` is not a column.{_close(name, columns)}")
        key = f"_bt{len(names)}_"
        names[key] = name
        return key

    return re.sub(r"`([^`]*)`", swap, text), names


def _close(name, columns) -> str:
    match = difflib.get_close_matches(str(name), [str(c) for c in columns], n=1, cutoff=0.6)
    if not match:
        match = [c for c in columns if str(c).lower() == str(name).lower()]
    return f" Did you mean '{match[0]}'?" if match else ""


class _Writer:
    """Walks the checked tree and writes pandas code."""

    def __init__(self, columns, aliases):
        self.columns = list(columns)
        self.aliases = aliases          # placeholder -> column name with spaces
        self.used: list = []
        self.count = 0

    def column(self, name: str) -> str:
        if name not in self.used:
            self.used.append(name)
        return f"df[{lit(name)}]"

    @staticmethod
    def truth(node, code: str, prec: int) -> tuple:
        """(code, precedence) of `node` as True / False for not / and / or (pandas writes them ~ & |, which on
        numbers would be bitwise: ~1 is -2, and floats with gaps can't be used at all). Comparisons, isna() and
        other logic are already True / False. For numbers 0 and a gap (NaN) count as False, anything else as
        True: a missing 0/1 flag is read as 'no'."""
        if isinstance(node, (ast.Compare, ast.BoolOp)) or (
                isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.Invert))) or (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("isna", "notna")):
            return code, prec
        if isinstance(node, ast.Constant):
            return repr(bool(node.value)), ATOM
        if isinstance(node, ast.Name):                     # a column
            return f"{code}.fillna(0).astype(bool)", ATOM
        return f"pd.Series({code}, index=df.index).fillna(0).astype(bool)", ATOM

    def write(self, node) -> tuple:
        """-> (code, precedence) for an expression node."""
        self.count += 1
        if self.count > MAX_NODES:
            raise ExprError("The formula is too long. Split it into two features.")
        if isinstance(node, ast.Expression):
            return self.write(node.body)
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool) or value is None:
                if value is None:
                    raise ExprError("None is not allowed; use isna(column) to test for gaps.")
                return repr(value), ATOM
            if isinstance(value, (int, float)):
                return lit(value), ATOM
            if isinstance(value, str):
                return lit(value), ATOM
            raise ExprError(f"{type(value).__name__} values are not allowed. {allowed_help()}")
        if isinstance(node, ast.Name):
            name = node.id
            if name.startswith("__"):
                raise ExprError(f"Names like {name} are not allowed. {allowed_help()}")
            if name in self.aliases:
                return self.column(self.aliases[name]), ATOM
            if name in self.columns:
                return self.column(name), ATOM
            if name in CONSTANTS:
                return CONSTANTS[name], ATOM
            if name in FUNCTIONS:
                raise ExprError(f"{name} is a function: write {name}(...) with a column inside.")
            raise ExprError(f"'{name}' is not a column.{_close(name, self.columns)} "
                            "Names with spaces go in backticks: `Flight Distance`.")
        if isinstance(node, ast.BinOp):
            kind = type(node.op)
            if kind not in BIN_OPS:
                raise ExprError(f"The operator in this formula is not allowed. {allowed_help()}")
            sym, prec = BIN_OPS[kind]
            left, lp = self.write(node.left)
            right, rp = self.write(node.right)
            if kind is ast.Pow:
                left = f"({left})" if lp <= prec else left
                right = f"({right})" if rp < prec else right
            else:
                left = f"({left})" if lp < prec else left
                right = f"({right})" if rp <= prec and kind in (ast.Sub, ast.Div, ast.FloorDiv, ast.Mod) or rp < prec \
                    else right
            return f"{left} {sym} {right}", prec
        if isinstance(node, ast.UnaryOp):
            inner, ip = self.write(node.operand)
            if isinstance(node.op, ast.USub):
                return f"-{inner}" if ip >= 7 else f"-({inner})", 7
            if isinstance(node.op, ast.UAdd):
                return inner, ip
            if isinstance(node.op, (ast.Not, ast.Invert)):
                inner, ip = self.truth(node.operand, inner, ip)
                return f"~({inner})" if ip < ATOM else f"~{inner}", 7
            raise ExprError(f"That operator is not allowed. {allowed_help()}")
        if isinstance(node, ast.Compare):
            parts, left = [], node.left
            for op, right in zip(node.ops, node.comparators):
                if type(op) not in COMPARE:
                    raise ExprError("Only < <= > >= == != comparisons are allowed (no 'in' or 'is').")
                a, ap = self.write(left)
                b, bp = self.write(right)
                a = f"({a})" if ap <= 4 else a
                b = f"({b})" if bp <= 4 else b
                parts.append(f"{a} {COMPARE[type(op)]} {b}")
                left = right
            if len(parts) == 1:
                return parts[0], 4
            return " & ".join(f"({p})" for p in parts), 2       # a < b < c -> (a < b) & (b < c)
        if isinstance(node, ast.BoolOp):
            sym, prec = ("&", 2) if isinstance(node.op, ast.And) else ("|", 1)
            items = []
            for value in node.values:
                code, p = self.truth(value, *self.write(value))
                items.append(code if p == ATOM else f"({code})")
            return f" {sym} ".join(items), prec
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ExprError(f"Only these functions can be called: {', '.join(FUNCTIONS)}. "
                                "Methods like x.str.len() are not allowed.")
            name = node.func.id
            if name not in FUNCTIONS:
                raise ExprError(f"'{name}' is not an allowed function. You can use: {', '.join(FUNCTIONS)}.")
            if node.keywords:
                raise ExprError(f"Write the values of {name}() in order, without name=value.")
            code, arity, _ = FUNCTIONS[name]
            ok = len(node.args) in arity if isinstance(arity, tuple) else len(node.args) == arity
            if not ok or any(isinstance(a, ast.Starred) for a in node.args):
                need = " or ".join(map(str, arity)) if isinstance(arity, tuple) else arity
                raise ExprError(f"{name}() takes {need} value(s): {FUNCTIONS[name][2]}.")
            args = ", ".join(self.write(a)[0] for a in node.args)
            if name == "where":
                return f"pd.Series(np.where({args}), index=df.index)", ATOM
            return f"{code}({args})", ATOM
        if isinstance(node, ast.Attribute):
            raise ExprError("Attribute access (like x.y or df.Fare) is not allowed: write the column name alone. "
                            + allowed_help())
        if isinstance(node, ast.Subscript):
            raise ExprError("Indexing with [ ] is not allowed: write the column name alone "
                            "(backticks for names with spaces).")
        if isinstance(node, ast.Lambda):
            raise ExprError("lambda is not allowed. " + allowed_help())
        if isinstance(node, ast.IfExp):
            raise ExprError("'a if condition else b' is not allowed: write where(condition, a, b).")
        raise ExprError(f"'{type(node).__name__}' is not allowed in a formula. {allowed_help()}")


def compile_expr(text: str, columns) -> tuple:
    """Check a formula and write it as pandas code.

    -> (code, used_columns). The code reads columns as df['name'] and uses np / pd only.
    Raises ExprError (with a message for people) for anything outside the allow-list.
    """
    text = (text or "").strip()
    if not text:
        raise ExprError("Type a formula, e.g. Fare / (SibSp + Parch + 1).")
    if len(text) > MAX_LENGTH:
        raise ExprError(f"The formula is longer than {MAX_LENGTH} characters.")
    if any(ord(ch) < 32 and ch != "\t" or ch in "\x85\u2028\u2029" for ch in text):
        raise ExprError("A formula is one line: remove the line breaks (or other control characters) from it.")
    columns = [str(c) for c in columns]
    source, aliases = _backticks(text, columns)
    try:
        tree = ast.parse(source, mode="eval")      # parses only: nothing is run
    except SyntaxError as exc:
        raise ExprError(f"That is not a valid formula ({exc.msg}). Example: Fare / (SibSp + Parch + 1).") from None
    writer = _Writer(columns, aliases)
    code, _ = writer.write(tree)
    if not writer.used:
        raise ExprError("Use at least one column in the formula.")
    return code, writer.used


def column_ref(name: str) -> str:
    """How a formula refers to a column: the bare name when it can be one, else `in backticks`."""
    bare = (name.isidentifier() and not keyword.iskeyword(name) and name not in FUNCTIONS
            and name not in CONSTANTS)
    return name if bare else f"`{name}`"


def rename_column(text: str, old: str, new: str) -> str:
    """The formula with every reference to column `old` (bare or `in backticks`) pointing to `new`. Text inside
    quotes, numbers and other names stay as they are."""
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "'\"":                                   # a string: copied as it is (escapes, triple quotes)
            quote = text[i:i + 3] if text[i:i + 3] in ("'" * 3, '"' * 3) else ch
            j = i + len(quote)
            while j < n and text[j:j + len(quote)] != quote:
                j += 2 if text[j] == "\\" else 1
            j = min(n, j + len(quote))
            out.append(text[i:j])
            i = j
        elif ch == "`":
            j = text.find("`", i + 1)
            j = n if j < 0 else j
            out.append(column_ref(new) if text[i + 1:j] == old else text[i:j + 1])
            i = j + 1
        elif ch.isdigit() or (ch == "." and text[i + 1:i + 2].isdigit()):
            j = i + 1                                     # a number such as 1e5 or 2.5
            while j < n and (text[j].isalnum() or text[j] in "._"):
                j += 1
            out.append(text[i:j])
            i = j
        elif ch.isidentifier():
            j = i + 1
            while j < n and ("a" + text[j]).isidentifier():
                j += 1
            word = text[i:j]
            out.append(column_ref(new) if word == old else word)
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def default_name(text: str, taken) -> str:
    """A column name made from the formula: 'Fare / (SibSp + Parch + 1)' -> 'Fare_per_SibSp_Parch'."""
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text.replace("/", " per "))
    words = [w for w in words if w not in FUNCTIONS and w not in CONSTANTS][:4]
    base = "_".join(words) or "my_feature"
    name, i = base[:40], 2
    while name in set(taken):
        name = f"{base[:36]}_{i}"
        i += 1
    return name
