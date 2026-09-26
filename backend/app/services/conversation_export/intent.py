"""Detects "export this conversation as a document" requests in free text,
and which format was meant. Deliberately narrow — a verb phrase *and* a
format/conversation noun, not a bag of words — so ordinary Document Agent
chatter ("summarize this report") never false-positives into an export.
"""

from __future__ import annotations

from typing import Literal

ExportFormat = Literal["docx", "pptx", "xlsx", "pdf"]

DEFAULT_FORMAT: ExportFormat = "docx"

_EXPORT_VERBS = [
    "generate", "make", "create", "export", "give me", "produce",
    "build", "download", "turn this into", "save this as",
]

# Checked in this priority order: a message naming more than one format noun
# (rare) resolves to whichever group is checked first.
_FORMAT_NOUNS: dict[ExportFormat, list[str]] = {
    "pptx": ["ppt", "pptx", "powerpoint", "slide", "slides", "slideshow", "presentation"],
    "xlsx": ["excel", "xlsx", "sheet", "spreadsheet"],
    "pdf": ["pdf"],
    "docx": ["word", "doc", "docx", "document", "report"],
}

# A reference to the conversation itself — combined with an export verb,
# this alone is enough signal even with no format noun (format then falls
# back to DEFAULT_FORMAT).
_CONVERSATION_NOUNS = [
    "this chat", "this conversation", "our discussion", "our chat",
    "this discussion", "of this chat", "of our discussion",
]

_ANY_FORMAT_NOUN = [noun for nouns in _FORMAT_NOUNS.values() for noun in nouns]


def is_export_request(message: str) -> bool:
    lowered = message.lower()
    has_verb = any(verb in lowered for verb in _EXPORT_VERBS)
    if not has_verb:
        return False
    return any(noun in lowered for noun in _ANY_FORMAT_NOUN) or any(
        noun in lowered for noun in _CONVERSATION_NOUNS
    )


def detect_export_format(message: str) -> ExportFormat:
    lowered = message.lower()
    for fmt, nouns in _FORMAT_NOUNS.items():
        if any(noun in lowered for noun in nouns):
            return fmt
    return DEFAULT_FORMAT
