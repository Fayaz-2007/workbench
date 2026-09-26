"""`DocumentSpec` — the one format-agnostic intermediate structure every
renderer (`docx`/`pptx`/`xlsx`/`pdf`, see `renderers.py`) consumes. Content
is generated exactly once (`pipeline.py`) and rendered N times, never the
other way around.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SectionSpec(BaseModel):
    heading: str
    paragraphs: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    code_blocks: list["CodeBlock"] = Field(default_factory=list)

    def word_count(self) -> int:
        text = " ".join(self.paragraphs) + " " + " ".join(self.bullets)
        return len(text.split())


class CodeBlock(BaseModel):
    language: str = ""
    code: str


class QAEntry(BaseModel):
    question: str
    answer: str


class ReferenceEntry(BaseModel):
    label: str
    source: str = ""


class DocumentMetadata(BaseModel):
    conversation_id: str
    generated_at: str
    models_used: list[str] = Field(default_factory=list)
    message_count: int = 0
    # Prominently rendered on every format's first page/slide/sheet so
    # mock output is never mistaken for a real generation (mirrors
    # `app/agents/base.py`'s development_notice()/real_inference_notice()
    # symmetry, applied to a generated *file* instead of a chat response).
    generation_notice: str = ""
    # How the final 6-8 section outline was arrived at (see
    # `pipeline.normalize_outline`): "model" (the LLM's own outline needed
    # no help), "fallback" (JSON parsing failed twice, fixed default
    # outline used), or "model+padded" (the model's outline was short, so
    # deterministic canonical sections were added to reach 6).
    outline_source: str = "model"
    outline_padded: int = 0


class DocumentSpec(BaseModel):
    title: str
    subtitle: str = ""
    metadata: DocumentMetadata
    sections: list[SectionSpec] = Field(default_factory=list)
    qa_log: list[QAEntry] = Field(default_factory=list)
    references: list[ReferenceEntry] = Field(default_factory=list)

    def total_word_count(self) -> int:
        return sum(s.word_count() for s in self.sections)

    def all_code_blocks(self) -> list[CodeBlock]:
        return [cb for section in self.sections for cb in section.code_blocks]


SectionSpec.model_rebuild()
