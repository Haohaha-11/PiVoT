"""Deterministic checks the model delegates instead of doing them in its head.

The model emits one of
    {"kind": "arith",   "expr": "200e6 / 2e9 * 100", "op": "==", "value": "10"}
    {"kind": "version", "left": "2.6", "op": ">=", "right": "2.4"}
    {"kind": "date",    "from": "2026-03-03", "to": "2026-03-13", "unit": "days", "op": "==", "value": "10"}
and we evaluate it. Only a tiny, safe subset is accepted: numbers, + - * / ** ( ), unit
suffixes and ISO dates. Anything else returns None (check ignored, never an exception).

Tolerance for "==" is decided here, not by the model: 1% relative by default, 10% when the
claim is hedged ("about", "roughly", ...). Documentation writes "4MB" for 4,000,000 or
4,194,304 bytes interchangeably, so KB/MB/GB/TB are evaluated under both the 1000 and the
1024 convention: "==" holds if either convention matches; an inequality whose outcome
depends on the convention is ambiguous and returns None. KiB/MiB/GiB are always binary.
"""
import ast
import datetime as dt
import operator
import re
from typing import Optional

EXACT_TOLERANCE = 0.01
HEDGED_TOLERANCE = 0.10
_HEDGE = re.compile(r"\b(?:about|approximately|approx\.?|roughly|around|nearly|almost|close to|on the order of"
                    r"|circa|ca\.)\s|~", re.I)

_MAGNITUDE = {"k": 1e3, "m": 1e6, "b": 1e9, "g": 1e9, "t": 1e12}
_BINARY = {"kib": 1024, "mib": 1024 ** 2, "gib": 1024 ** 3, "tib": 1024 ** 4}
_AMBIGUOUS_BYTES = {"kb": 1, "mb": 2, "gb": 3, "tb": 4}  # power of the base
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow}
_CMP = {"==": operator.eq, "=": operator.eq, "!=": operator.ne, "<": operator.lt,
        "<=": operator.le, ">": operator.gt, ">=": operator.ge}
_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kib|mib|gib|tib|kb|mb|gb|tb|k|m|b|g|t)\b|(\d+(?:\.\d+)?)\s*%", re.I)
_DAYS_PER = {"days": 1, "day": 1, "weeks": 7, "week": 7, "months": 30.44, "month": 30.44, "years": 365.25, "year": 365.25}


def is_hedged(text: str) -> bool:
    return bool(_HEDGE.search(f"{text} "))


def _expand_units(s: str, byte_base: int = 1024) -> str:
    # Single-letter suffixes are magnitudes (M = million); byte units use KB/MB/GB.
    s = s.replace(",", "").replace("×", "*")

    def sub(m):
        if m.group(3):
            return m.group(3)
        num, unit = m.group(1), m.group(2).lower()
        if unit in _BINARY:
            factor = _BINARY[unit]
        elif unit in _AMBIGUOUS_BYTES:
            factor = byte_base ** _AMBIGUOUS_BYTES[unit]
        else:
            factor = _MAGNITUDE[unit]
        return f"({num}*{factor})"

    return _UNIT_RE.sub(sub, s)


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        l, r = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(r) > 64:
            raise ValueError("exponent too large")
        return _BIN[type(node.op)](l, r)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    raise ValueError(f"disallowed node {type(node).__name__}")


def eval_number(expr: str, byte_base: int = 1024) -> Optional[float]:
    expr = str(expr).strip()
    if not expr or len(expr) > 200:
        return None
    try:
        return _eval(ast.parse(_expand_units(expr, byte_base), mode="eval"))
    except Exception:
        return None


def _version(v: str):
    parts = re.findall(r"\d+", str(v))
    return tuple(int(p) for p in parts) if parts else None


def _date(v: str) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def _compare(op, left: float, right: float, tol: float) -> bool:
    if op is operator.eq:
        return abs(left - right) <= tol * max(abs(left), abs(right), 1e-12)
    if op is operator.ne:
        return abs(left - right) > tol * max(abs(left), abs(right), 1e-12)
    return op(left, right)


def run_check(check: dict, hedged: bool = False) -> Optional[bool]:
    """True/False when the check is well-formed and evaluable, else None.
    `hedged`: the claim itself says "about"/"roughly"/... (decided by the caller from the claim text)."""
    if not isinstance(check, dict):
        return None
    op = _CMP.get(str(check.get("op", "==")).strip())
    if op is None:
        return None
    tol = HEDGED_TOLERANCE if hedged else EXACT_TOLERANCE  # model-supplied tolerance is ignored on purpose
    kind = check.get("kind", "arith")
    if kind == "version":
        l, r = _version(check.get("left")), _version(check.get("right"))
        if l is None or r is None:
            return None
        n = max(len(l), len(r))
        return op(l + (0,) * (n - len(l)), r + (0,) * (n - len(r)))
    if kind == "date":
        a, b = _date(check.get("from")), _date(check.get("to"))
        per = _DAYS_PER.get(str(check.get("unit", "days")).strip().lower())
        value = eval_number(check.get("value", ""))
        if a is None or b is None or per is None or value is None:
            return None
        return _compare(op, (b - a).days / per, value, tol)
    outcomes = set()
    for base in (1024, 1000):
        left = eval_number(check.get("expr", check.get("left", "")), base)
        right = eval_number(check.get("value", check.get("right", "")), base)
        if left is None or right is None:
            return None
        outcomes.add(_compare(op, left, right, tol))
    if op is operator.eq:
        return True in outcomes
    return outcomes.pop() if len(outcomes) == 1 else None
