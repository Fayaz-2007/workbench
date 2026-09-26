"""Deterministic outline normalization — no I/O, no LLM calls.

`qwen2.5:1.5b` was asked for 6-8 sections but, observed in practice, hands
back anywhere from 2 to 8+. `normalize_outline()` takes whatever the model
(or the fixed fallback outline) produced and deterministically turns it
into a clean 6-8 section list every time: dedupe, detect which canonical
topics are already covered, pad the gaps, cap the overflow, then order.
"""

from __future__ import annotations

import re

logger_name = __name__

MIN_SECTIONS = 6
MAX_SECTIONS = 8

# The one canonical list `normalize_outline()` measures coverage and pads
# against — kept as a single constant, in the order a finished document
# should read in. Keywords are matched as substrings of a section's own
# *normalized heading* (not its body), so they're deliberately short and
# distinctive rather than exhaustive.
CANONICAL_SECTIONS: list[dict[str, object]] = [
    {
        "heading": "Executive Summary",
        "focus": "a brief high-level summary of the whole conversation",
        "keywords": ["executive summary", "high-level summary", "overview"],
    },
    {
        "heading": "Background & Context",
        "focus": "what the conversation was about and why it started",
        "keywords": ["background", "context"],
    },
    {
        "heading": "Key Discussion Points",
        "focus": "the main topics and questions raised",
        "keywords": ["discussion point", "key point", "key topic", "topics discussed"],
    },
    {
        "heading": "Detailed Analysis",
        "focus": "the substantive reasoning, explanations, or analysis given",
        "keywords": ["detailed analysis", "analysis", "deep dive"],
    },
    {
        "heading": "Findings",
        "focus": "facts, answers and results established in the conversation",
        "keywords": ["finding", "result", "observation", "key result"],
    },
    {
        "heading": "Decisions & Recommendations",
        "focus": "any decisions made or recommendations given",
        "keywords": ["decision", "recommendation"],
    },
    {
        "heading": "Action Items / Next Steps",
        "focus": "follow-up actions or next steps mentioned",
        "keywords": ["action item", "action", "next step", "todo", "to-do", "follow-up"],
    },
    {
        "heading": "Conclusion",
        "focus": "a short closing summary",
        "keywords": ["conclusion", "closing", "wrap-up", "wrap up"],
    },
]

EXEC_SUMMARY_INDEX = 0
CONCLUSION_INDEX = len(CANONICAL_SECTIONS) - 1

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[.,;:!?]+$")


def _normalize_heading_key(heading: str) -> str:
    """Lowercase, punctuation-stripped, whitespace-collapsed form used for
    both duplicate detection and canonical-keyword matching.
    """
    text = _PUNCTUATION_RE.sub(" ", heading.lower())
    return _WHITESPACE_RE.sub(" ", text).strip()


def _covers(heading_key: str, canonical_index: int) -> bool:
    keywords = CANONICAL_SECTIONS[canonical_index]["keywords"]
    return any(kw in heading_key for kw in keywords)


def _first_covered_index(heading_key: str) -> int | None:
    for i in range(len(CANONICAL_SECTIONS)):
        if _covers(heading_key, i):
            return i
    return None


def _clean(sections: list[dict]) -> list[dict]:
    """Strips whitespace/trailing punctuation from headings, drops empty
    ones, and removes duplicates (case/punctuation-insensitive).
    """
    cleaned: list[dict] = []
    seen_keys: set[str] = set()
    for entry in sections:
        heading = str(entry.get("heading", "")).strip()
        heading = _TRAILING_PUNCT_RE.sub("", heading).strip()
        if not heading:
            continue
        key = _normalize_heading_key(heading)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        focus = str(entry.get("focus") or heading).strip()
        cleaned.append({"heading": heading, "focus": focus})
    return cleaned


def _pad(cleaned: list[dict]) -> tuple[list[dict], int]:
    """Adds missing canonical sections until there are `MIN_SECTIONS` —
    skipping any canonical topic a cleaned section already covers.

    Executive Summary and Conclusion are filled first when missing (ahead
    of the other, non-bookend canonical topics) so a padded outline always
    still has both — the same two sections `_cap()` refuses to drop and
    `_order()` anchors to front/back. Filling strictly in canonical order
    instead can exhaust `MIN_SECTIONS` on middle topics before ever
    reaching Conclusion, leaving the document without a closing section.
    The remaining slots are still filled in canonical order.
    """
    if len(cleaned) >= MIN_SECTIONS:
        return cleaned, 0

    covered: set[int] = set()
    for entry in cleaned:
        idx = _first_covered_index(_normalize_heading_key(entry["heading"]))
        if idx is not None:
            covered.add(idx)

    needed = MIN_SECTIONS - len(cleaned)
    bookend_indices = [i for i in (EXEC_SUMMARY_INDEX, CONCLUSION_INDEX) if i not in covered]
    other_indices = [
        i for i in range(len(CANONICAL_SECTIONS)) if i not in covered and i not in bookend_indices
    ]

    padded_entries: list[dict] = []
    for i in bookend_indices + other_indices:
        if needed <= 0:
            break
        canon = CANONICAL_SECTIONS[i]
        padded_entries.append({"heading": canon["heading"], "focus": canon["focus"], "padded": True})
        needed -= 1

    return cleaned + padded_entries, len(padded_entries)


def _cap(sections: list[dict]) -> list[dict]:
    """Keeps the first `MAX_SECTIONS`, except a section covering Executive
    Summary or Conclusion is never dropped — a non-protected section from
    the middle is dropped in its place instead.
    """
    if len(sections) <= MAX_SECTIONS:
        return sections

    def is_protected(entry: dict) -> bool:
        idx = _first_covered_index(_normalize_heading_key(entry["heading"]))
        return idx in (EXEC_SUMMARY_INDEX, CONCLUSION_INDEX)

    kept = sections[:MAX_SECTIONS]
    overflow = sections[MAX_SECTIONS:]

    for entry in overflow:
        if not is_protected(entry):
            continue
        # Make room by dropping the last non-protected section already in
        # `kept` (i.e. from the middle, never the front) instead of simply
        # truncating this protected one away.
        for i in range(len(kept) - 1, -1, -1):
            if not is_protected(kept[i]):
                kept.pop(i)
                break
        kept.append(entry)

    return kept


def _order(sections: list[dict]) -> list[dict]:
    """Canonical-anchored sections (model or padded) sort by canonical
    index first, preserving relative order otherwise; sections with no
    canonical match ("custom" headings) keep their relative order after
    them. Then Executive Summary is forced to the front and Conclusion to
    the back, whatever their coverage-based position left them at.
    """
    annotated = [
        (_first_covered_index(_normalize_heading_key(entry["heading"])), original_index, entry)
        for original_index, entry in enumerate(sections)
    ]
    annotated.sort(key=lambda t: (t[0] if t[0] is not None else len(CANONICAL_SECTIONS), t[1]))
    ordered = [entry for _, _, entry in annotated]

    def move(predicate, to_front: bool) -> None:
        idx = next((i for i, e in enumerate(ordered) if predicate(e)), None)
        if idx is None:
            return
        item = ordered.pop(idx)
        ordered.insert(0, item) if to_front else ordered.append(item)

    move(lambda e: _first_covered_index(_normalize_heading_key(e["heading"])) == EXEC_SUMMARY_INDEX, to_front=True)
    move(lambda e: _first_covered_index(_normalize_heading_key(e["heading"])) == CONCLUSION_INDEX, to_front=False)

    return ordered


def normalize_outline(sections: list[dict]) -> tuple[list[dict], int]:
    """Cleans, pads, caps, and orders a raw outline section list into a
    deterministic 6-8 section list. Returns `(sections, padded_count)`.
    Pure — no LLM calls, no I/O.
    """
    cleaned = _clean(sections)
    padded, padded_count = _pad(cleaned)
    capped = _cap(padded)
    ordered = _order(capped)
    return ordered, padded_count
