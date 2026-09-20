"""ReportGenerationTool — assembles and writes a real report file, reusing
DocumentGenerationTool's writers.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_report_generation_writes_markdown(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings
    from app.tools.report_generation import ReportGenerationTool

    monkeypatch.setattr(get_settings(), "generated_dir", str(tmp_path / "generated"))

    result = await ReportGenerationTool().execute(
        {
            "title": "System Security Report",
            "task": "Analyze system security status",
            "data_sources": ["Local system", "Local network", "security_policy.pdf"],
            "findings": "CPU 12%, RAM 40%. 3 local connections, 0 external.",
            "ai_analysis": "Nothing unusual was observed.",
            "citations": ["security_policy.pdf (p.4)"],
            "sovereignty_status": "LOCAL",
            "format": "md",
        }
    )
    assert result.success, result.error
    generated = tmp_path / "generated" / result.output["filename"]
    assert generated.exists()
    text = generated.read_text(encoding="utf-8")
    assert "## Task" in text
    assert "## Findings (observed facts)" in text
    assert "## AI Analysis (interpretation)" in text
    assert "security_policy.pdf" in text


@pytest.mark.asyncio
async def test_report_generation_rejects_bad_format() -> None:
    from app.tools.report_generation import ReportGenerationTool

    result = await ReportGenerationTool().execute({"title": "x", "task": "y", "format": "exe"})
    assert not result.success
