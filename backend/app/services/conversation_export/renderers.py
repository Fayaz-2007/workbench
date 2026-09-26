"""Format renderers — each takes the same `DocumentSpec` (see `spec.py`)
and produces one file. Content is generated exactly once (`pipeline.py`);
these functions only lay it out differently per format, never regenerate
it — so DOCX/PPTX/XLSX/PDF exports of the same conversation always agree
on what was actually said.

Builds on the same libraries `app/tools/document_generation.py` already
uses (python-docx, openpyxl, fpdf2) plus python-pptx (new, offline-only —
no external images or fonts are fetched at runtime).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.conversation_export.intent import ExportFormat

if TYPE_CHECKING:
    from app.services.conversation_export.spec import DocumentSpec

TYPE_LABELS: dict[ExportFormat, str] = {
    "docx": "Word Document",
    "pptx": "PowerPoint Presentation",
    "xlsx": "Excel Spreadsheet",
    "pdf": "PDF Document",
}

_ACCENT_RGB = (0x1F, 0x4E, 0x79)  # a single consistent accent colour, used across docx/pptx/xlsx
_ACCENT_HEX = "1F4E79"


# ---- DOCX --------------------------------------------------------------


def _render_docx(spec: "DocumentSpec", target: Path) -> None:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    def add_field(paragraph, field_code: str) -> None:
        run = paragraph.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = field_code
        separate = OxmlElement("w:fldChar")
        separate.set(qn("w:fldCharType"), "separate")
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(begin)
        run._r.append(instr)
        run._r.append(separate)
        run._r.append(end)

    def shade_paragraph(paragraph, hex_color: str) -> None:
        pPr = paragraph._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        pPr.append(shd)

    document = docx.Document()

    # --- Title page ---
    title_p = document.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run(spec.title)
    title_run.font.size = Pt(28)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(*_ACCENT_RGB)

    if spec.subtitle:
        sub_p = document.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = sub_p.add_run(spec.subtitle)
        sub_run.font.size = Pt(14)
        sub_run.font.italic = True

    notice_p = document.add_paragraph()
    notice_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    notice_p.add_run(spec.metadata.generation_notice).font.italic = True

    meta_p = document.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_p.add_run(
        f"Conversation: {spec.metadata.conversation_id}  ·  "
        f"Generated: {spec.metadata.generated_at}  ·  "
        f"Messages: {spec.metadata.message_count}  ·  "
        f"Model(s): {', '.join(spec.metadata.models_used) or 'n/a'}"
    ).font.size = Pt(9)
    document.add_page_break()

    # --- Table of contents (Word field — press F9 / "Update Field" to populate) ---
    document.add_heading("Table of Contents", level=1)
    toc_note = document.add_paragraph()
    toc_note.add_run("(Right-click and choose \"Update Field\" in Word to populate this table.)").font.italic = True
    toc_p = document.add_paragraph()
    add_field(toc_p, 'TOC \\o "1-2" \\h \\z \\u')
    document.add_page_break()

    # --- Sections ---
    for section in spec.sections:
        document.add_heading(section.heading, level=1)
        for paragraph_text in section.paragraphs:
            document.add_paragraph(paragraph_text)
        for bullet in section.bullets:
            document.add_paragraph(bullet, style="List Bullet")
        for code_block in section.code_blocks:
            code_p = document.add_paragraph()
            shade_paragraph(code_p, "EFEFEF")
            for i, line in enumerate(code_block.code.splitlines() or [""]):
                run = code_p.add_run(line if i == 0 else "\n" + line)
                run.font.name = "Courier New"
                run.font.size = Pt(9)

    # --- Q&A log ---
    if spec.qa_log:
        document.add_heading("Key Q&A Log", level=1)
        table = document.add_table(rows=1, cols=2)
        table.style = "Light Grid Accent 1"
        header_cells = table.rows[0].cells
        header_cells[0].text = "Question"
        header_cells[1].text = "Answer"
        for entry in spec.qa_log:
            row = table.add_row().cells
            row[0].text = entry.question
            row[1].text = entry.answer

    # --- References ---
    if spec.references:
        document.add_heading("References", level=1)
        for ref in spec.references:
            document.add_paragraph(ref.label, style="List Bullet")

    # --- Page numbers in the footer ---
    footer = document.sections[0].footer
    footer_p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer_p, "PAGE")

    document.save(str(target))


# ---- PPTX ---------------------------------------------------------------

_MAX_BULLETS_PER_SLIDE = 5
# Keeps the deck within the ~8-10 total slide target from the spec: Title +
# Agenda + up to 5 key-section slides + Key Q&A + Decisions + Conclusion.
# Sections beyond the first 5 still appear in the Agenda and in full in the
# DOCX/PDF/XLSX exports — the deck is a summary, not the full document.
_MAX_SECTION_SLIDES = 5


def _section_bullet_points(section) -> list[str]:
    """Full-sentence bullet points for a slide — the section's own bullets
    if the model produced any, otherwise each paragraph stands on its own
    (still a full sentence/thought, never a fragment).
    """
    points = list(section.bullets)
    if not points:
        points = list(section.paragraphs)
    return points or [f"({section.heading} — no content captured)"]


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)] or [[]]


def _render_pptx(spec: "DocumentSpec", target: Path) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    accent = RGBColor(*_ACCENT_RGB)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def new_slide():
        return prs.slides.add_slide(blank_layout)

    def add_title_bar(slide, text: str) -> None:
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(1.1))
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        bar.line.fill.background()
        text_frame = bar.text_frame
        text_frame.margin_left = Inches(0.4)
        text_frame.word_wrap = True
        paragraph = text_frame.paragraphs[0]
        paragraph.text = text
        paragraph.font.size = Pt(28)
        paragraph.font.bold = True
        paragraph.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    def add_slide_number(slide, n: int) -> None:
        box = slide.shapes.add_textbox(prs.slide_width - Inches(0.9), prs.slide_height - Inches(0.5), Inches(0.7), Inches(0.4))
        paragraph = box.text_frame.paragraphs[0]
        paragraph.text = str(n)
        paragraph.font.size = Pt(11)
        paragraph.alignment = PP_ALIGN.RIGHT

    def add_bullets(slide, points: list[str], top: float = 1.4) -> None:
        box = slide.shapes.add_textbox(Inches(0.6), Inches(top), prs.slide_width - Inches(1.2), prs.slide_height - Inches(top) - Inches(0.5))
        text_frame = box.text_frame
        text_frame.word_wrap = True
        for i, point in enumerate(points):
            paragraph = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
            paragraph.text = f"• {point}"
            paragraph.font.size = Pt(20)
            paragraph.space_after = Pt(14)

    def set_notes(slide, text: str) -> None:
        if text.strip():
            slide.notes_slide.notes_text_frame.text = text

    slide_number = 1

    # 1. Title slide
    title_slide = new_slide()
    box = title_slide.shapes.add_textbox(Inches(1), Inches(2.6), prs.slide_width - Inches(2), Inches(2))
    tf = box.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = spec.title
    p0.font.size = Pt(40)
    p0.font.bold = True
    p0.font.color.rgb = accent
    p0.alignment = PP_ALIGN.CENTER
    if spec.subtitle:
        p1 = tf.add_paragraph()
        p1.text = spec.subtitle
        p1.font.size = Pt(20)
        p1.font.italic = True
        p1.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    p2.text = spec.metadata.generation_notice
    p2.font.size = Pt(12)
    p2.alignment = PP_ALIGN.CENTER
    add_slide_number(title_slide, slide_number)
    slide_number += 1

    # 2. Agenda
    agenda_slide = new_slide()
    add_title_bar(agenda_slide, "Agenda")
    add_bullets(agenda_slide, [s.heading for s in spec.sections])
    add_slide_number(agenda_slide, slide_number)
    slide_number += 1

    # 3. One slide per section (split into multiple if bullets don't fit)
    for section in spec.sections[:_MAX_SECTION_SLIDES]:
        points = _section_bullet_points(section)
        notes = "\n\n".join(section.paragraphs) if section.paragraphs else ""
        chunks = _chunk(points, _MAX_BULLETS_PER_SLIDE)
        for i, chunk in enumerate(chunks):
            heading = section.heading if i == 0 else f"{section.heading} (cont.)"
            slide = new_slide()
            add_title_bar(slide, heading)
            add_bullets(slide, chunk)
            set_notes(slide, notes)
            add_slide_number(slide, slide_number)
            slide_number += 1

    # 4. Key Q&A slide — a single slide, first 5 entries (the full log is
    # still in the DOCX/PDF/XLSX exports).
    if spec.qa_log:
        qa_points = [f"Q: {e.question}  —  A: {e.answer}" for e in spec.qa_log[:_MAX_BULLETS_PER_SLIDE]]
        slide = new_slide()
        add_title_bar(slide, "Key Q&A")
        add_bullets(slide, qa_points)
        add_slide_number(slide, slide_number)
        slide_number += 1

    # 5. Decisions & Next Steps — pulled from any section whose heading
    # suggests decisions/next-steps content; falls back to a references
    # summary so the slide is never empty.
    decision_points: list[str] = []
    for section in spec.sections:
        if any(word in section.heading.lower() for word in ("decision", "next step", "action", "recommend")):
            decision_points.extend(_section_bullet_points(section))
    if not decision_points:
        decision_points = ["No explicit decisions or next steps were captured in this conversation."]
    decision_slide = new_slide()
    add_title_bar(decision_slide, "Decisions & Next Steps")
    add_bullets(decision_slide, decision_points[:_MAX_BULLETS_PER_SLIDE])
    add_slide_number(decision_slide, slide_number)
    slide_number += 1

    # 6. Conclusion / Summary
    conclusion_section = next((s for s in spec.sections if "conclusion" in s.heading.lower()), spec.sections[-1] if spec.sections else None)
    conclusion_points = _section_bullet_points(conclusion_section) if conclusion_section else ["End of summary."]
    conclusion_slide = new_slide()
    add_title_bar(conclusion_slide, "Conclusion")
    add_bullets(conclusion_slide, conclusion_points[:_MAX_BULLETS_PER_SLIDE])
    add_slide_number(conclusion_slide, slide_number)

    prs.save(str(target))


# ---- XLSX ---------------------------------------------------------------


def _render_xlsx(spec: "DocumentSpec", target: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    bold = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")

    def style_header(sheet, row: int, n_cols: int) -> None:
        for col in range(1, n_cols + 1):
            sheet.cell(row=row, column=col).font = bold
        sheet.freeze_panes = sheet.cell(row=row + 1, column=1).coordinate

    def set_widths(sheet, widths: list[int]) -> None:
        for i, width in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(i)].width = width

    # --- Summary ---
    summary = workbook.active
    summary.title = "Summary"
    summary.append([spec.title])
    summary.cell(row=1, column=1).font = Font(bold=True, size=16)
    if spec.subtitle:
        summary.append([spec.subtitle])
    summary.append([])
    summary.append(["Generated", spec.metadata.generated_at])
    summary.append(["Conversation ID", spec.metadata.conversation_id])
    summary.append(["Messages", spec.metadata.message_count])
    summary.append(["Model(s)", ", ".join(spec.metadata.models_used)])
    summary.append(["Notice", spec.metadata.generation_notice])
    summary.append([])
    exec_section = spec.sections[0] if spec.sections else None
    if exec_section:
        summary.append([f"{exec_section.heading}"])
        summary.cell(row=summary.max_row, column=1).font = bold
        for paragraph in exec_section.paragraphs:
            summary.append([paragraph])
            summary.cell(row=summary.max_row, column=1).alignment = wrap
    set_widths(summary, [100])

    # --- Key Points ---
    key_points = workbook.create_sheet("Key Points")
    key_points.append(["Section", "Point"])
    for section in spec.sections:
        for point in (section.bullets or section.paragraphs):
            key_points.append([section.heading, point])
    style_header(key_points, 1, 2)
    set_widths(key_points, [28, 100])
    for row in key_points.iter_rows(min_row=2):
        row[1].alignment = wrap

    # --- Q&A Log ---
    qa_sheet = workbook.create_sheet("Q&A Log")
    qa_sheet.append(["#", "Question", "Answer"])
    for i, entry in enumerate(spec.qa_log, start=1):
        qa_sheet.append([i, entry.question, entry.answer])
    style_header(qa_sheet, 1, 3)
    set_widths(qa_sheet, [6, 50, 80])
    for row in qa_sheet.iter_rows(min_row=2):
        row[1].alignment = wrap
        row[2].alignment = wrap

    # --- References ---
    refs_sheet = workbook.create_sheet("References")
    refs_sheet.append(["#", "Reference"])
    for i, ref in enumerate(spec.references, start=1):
        refs_sheet.append([i, ref.label])
    style_header(refs_sheet, 1, 2)
    set_widths(refs_sheet, [6, 80])

    workbook.save(str(target))


# ---- PDF ------------------------------------------------------------------

_UNICODE_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def _find_unicode_font() -> str | None:
    for candidate in _UNICODE_FONT_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return None


def _render_pdf(spec: "DocumentSpec", target: Path) -> None:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()

    font_family = "Helvetica"
    unicode_available = False
    font_path = _find_unicode_font()
    if font_path:
        try:
            pdf.add_font("Body", "", font_path)
            # Same face registered for "B" too — this machine only has a
            # regular-weight TTF available (see `_find_unicode_font`), and
            # `set_font(..., style="B")` raises if a bold face was never
            # registered. Text won't render visually bold, but Unicode
            # (₹, non-ASCII, ...) keeps working, which is the point.
            pdf.add_font("Body", "B", font_path)
            font_family = "Body"
            unicode_available = True
        except Exception:  # noqa: BLE001 - fall back to core font on any font-loading failure
            font_family = "Helvetica"

    def safe(text: str) -> str:
        if unicode_available:
            return text
        # Core PDF fonts (Helvetica/Times/Courier) are Latin-1 only — never
        # let an out-of-range character (₹, curly quotes, emoji, ...) crash
        # generation; substitute rather than fail.
        return text.encode("latin-1", "replace").decode("latin-1")

    def mc(h: float, text: str, **kw) -> None:
        # fpdf2's multi_cell defaults to new_x=RIGHT, which leaves the
        # cursor pinned at the page's right edge — the *next* multi_cell
        # call then sees ~0 remaining width and raises
        # "Not enough horizontal space to render a single character".
        # Always returning to the left margin on a new line avoids that.
        pdf.multi_cell(0, h, safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT, **kw)

    def add_footer() -> None:
        # Auto page-break triggers at `h - margin` (15mm from the bottom) —
        # exactly where the footer is drawn, so without disabling it here
        # first, drawing the footer itself spuriously starts a blank page.
        pdf.set_auto_page_break(False)
        pdf.set_y(-15)
        pdf.set_font(font_family, size=9)
        pdf.cell(0, 10, safe(f"Page {pdf.page_no()}/{{nb}}"), align="C")
        pdf.set_auto_page_break(True, margin=15)

    pdf.set_font(font_family, size=24)
    pdf.add_page()
    mc(12, spec.title, align="C")
    if spec.subtitle:
        pdf.set_font(font_family, size=14)
        mc(8, spec.subtitle, align="C")
    pdf.ln(4)
    pdf.set_font(font_family, size=10)
    mc(6, spec.metadata.generation_notice, align="C")
    pdf.ln(2)
    mc(
        6,
        f"Conversation: {spec.metadata.conversation_id} | Generated: {spec.metadata.generated_at} | "
        f"Messages: {spec.metadata.message_count} | Model(s): {', '.join(spec.metadata.models_used)}",
        align="C",
    )

    for section in spec.sections:
        pdf.add_page()
        pdf.set_font(font_family, size=18)
        mc(10, section.heading)
        pdf.ln(1)
        pdf.set_font(font_family, size=11)
        for paragraph in section.paragraphs:
            mc(6, paragraph)
            pdf.ln(2)
        for bullet in section.bullets:
            mc(6, f"-  {bullet}")
        for code_block in section.code_blocks:
            pdf.set_font("Courier", size=9)
            pdf.set_fill_color(239, 239, 239)
            mc(5, code_block.code, fill=True)
            pdf.set_font(font_family, size=11)
        add_footer()

    if spec.qa_log:
        pdf.add_page()
        pdf.set_font(font_family, size=18)
        mc(10, "Key Q&A Log")
        pdf.set_font(font_family, size=10)
        for entry in spec.qa_log:
            pdf.set_font(font_family, size=10, style="B")
            mc(6, f"Q: {entry.question}")
            pdf.set_font(font_family, size=10)
            mc(6, f"A: {entry.answer}")
            pdf.ln(2)
        add_footer()

    if spec.references:
        pdf.add_page()
        pdf.set_font(font_family, size=18)
        mc(10, "References")
        pdf.set_font(font_family, size=10)
        for ref in spec.references:
            mc(6, f"-  {ref.label}")
        add_footer()

    pdf.output(str(target))


_RENDERERS = {"docx": _render_docx, "pptx": _render_pptx, "xlsx": _render_xlsx, "pdf": _render_pdf}


def render_document(spec: "DocumentSpec", fmt: ExportFormat, target: Path) -> None:
    _RENDERERS[fmt](spec, target)
