"""Sentence segmentation with exact character offsets, and pointer rendering."""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Split after . ! ? (optionally followed by a closing quote/bracket) when whitespace
# follows, and on blank lines. Common abbreviations and decimals are protected.
_ABBREV = re.compile(r"\b(?:e\.g|i\.e|etc|vs|cf|Dr|Mr|Ms|Fig|approx)\.$", re.I)
_NUMERO = re.compile(r"\bNo\.$", re.I)  # "No. 5" is an abbreviation, "the default is no." ends a sentence
_BOUNDARY = re.compile(r"(?<=[.!?])([\"')\]]?)\s+|\n\s*\n")


@dataclass(frozen=True)
class Sentence:
    sid: str      # "P{passage}.S{n}" or "A.S{n}"
    passage: int  # -1 for answer sentences
    start: int
    end: int
    text: str


def split_sentences(text: str) -> List[Tuple[int, int]]:
    spans, start = [], 0
    for m in _BOUNDARY.finditer(text):
        cut = m.start() + len(m.group(1) or "")
        before = text[start:m.start()]
        if _ABBREV.search(before) or (_NUMERO.search(before) and text[m.end():m.end() + 1].isdigit()):
            continue
        if text[start:cut].strip():
            spans.append(_trim(text, start, cut))
        start = m.end()
    if text[start:].strip():
        spans.append(_trim(text, start, len(text)))
    return spans


def _trim(text: str, s: int, e: int) -> Tuple[int, int]:
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    return s, e


class PassageIndex:
    """All passage sentences addressable by ID. The only way a citation is created."""

    def __init__(self, passages: List[str]):
        self.passages = passages
        self.sentences: Dict[str, Sentence] = {}
        self.order: List[Sentence] = []
        for p, text in enumerate(passages):
            for n, (s, e) in enumerate(split_sentences(text)):
                sent = Sentence(f"P{p}.S{n}", p, s, e, text[s:e])
                self.sentences[sent.sid] = sent
                self.order.append(sent)

    def get(self, sid: str) -> Optional[Sentence]:
        return self.sentences.get(_normalize_sid(sid))

    def render(self) -> str:
        if not self.order:
            return "(no passages)"
        blocks, cur = [], None
        for s in self.order:
            if s.passage != cur:
                blocks.append(f"\n## Passage {s.passage}")
                cur = s.passage
            blocks.append(f"[{s.sid}] {s.text}")
        return "\n".join(blocks).strip()


def _normalize_sid(sid: str) -> str:
    """Accept harmless variants such as 'p0.s3', '[P0.S3]', 'P0 S3'."""
    m = re.fullmatch(r"\[?\s*P\s*(\d+)\s*[.\s:_-]?\s*S\s*(\d+)\s*\]?", str(sid).strip(), re.I)
    return f"P{int(m.group(1))}.S{int(m.group(2))}" if m else str(sid)


def locate(answer: str, anchor: str) -> Optional[List[int]]:
    """Find a claim anchor in the answer: exact, then whitespace/case-insensitive."""
    if not anchor:
        return None
    i = answer.find(anchor)
    if i >= 0:
        return [i, i + len(anchor)]
    pat = r"\s+".join(re.escape(t) for t in anchor.split())
    m = re.search(pat, answer, re.I) if pat else None
    return [m.start(), m.end()] if m else None
