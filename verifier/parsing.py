"""Tolerant JSON extraction. Every tolerance used is reported so it can be counted."""
import json
import re
from typing import List, Optional, Tuple


class ParseError(ValueError):
    pass


def parse_object(text: str, list_key: str = "claims") -> Tuple[dict, List[str]]:
    repairs: List[str] = []
    s = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    if m:
        s = m.group(1).strip()
        repairs.append("code_fence")
    obj = _loads(s)
    if obj is None:
        i, j = min((k for k in (s.find("{"), s.find("[")) if k >= 0), default=-1), max(s.rfind("}"), s.rfind("]"))
        obj = _loads(s[i:j + 1]) if 0 <= i < j else None
        if obj is None:
            raise ParseError("no JSON object found in model output")
        repairs.append("surrounding_text")
    if isinstance(obj, list):
        if len(obj) == 1 and isinstance(obj[0], dict) and list_key in obj[0]:
            obj = obj[0]
            repairs.append("unwrap_array")
        elif all(isinstance(x, dict) for x in obj):
            obj = {list_key: obj}
            repairs.append("bare_list")
    if not isinstance(obj, dict) or not isinstance(obj.get(list_key, []), list):
        raise ParseError(f"expected an object with a '{list_key}' list")
    obj.setdefault(list_key, [])
    return obj, repairs


def _loads(s: str) -> Optional[object]:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None
