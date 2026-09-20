"""Tool Registry, Calculator, and file tools — including the path-escape
guard every file tool relies on.
"""

from __future__ import annotations

import pytest

from app.tools.calculator import UnsafeExpressionError, safe_eval
from app.tools.file_tools import FileReadTool, FileWriteTool, ListFilesTool
from app.tools.fs_utils import PathEscapeError, resolve_within
from app.tools.registry import ToolNotFoundError, ToolRegistry


def test_registry_register_get_list() -> None:
    registry = ToolRegistry()
    registry.register(FileReadTool())
    registry.register(ListFilesTool())

    assert registry.get("file_read").name == "file_read"
    names = {m.name for m in registry.list()}
    assert names == {"file_read", "list_files"}


def test_registry_unknown_tool_raises() -> None:
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get("does-not-exist")


def test_registry_list_for_capabilities() -> None:
    registry = ToolRegistry()
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    matches = registry.list_for_capabilities(["local_file_write"])
    assert [t.name for t in matches] == ["file_write"]


# --- calculator ---------------------------------------------------------


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 2", 4),
        ("(3 + 4) * 2", 14),
        ("10 / 4", 2.5),
        ("2 ** 10", 1024),
        ("sqrt(16)", 4.0),
        ("round(3.14159, 2)", 3.14),
        ("max(1, 5, 3)", 5),
    ],
)
def test_safe_eval(expression: str, expected: float) -> None:
    assert safe_eval(expression) == expected


@pytest.mark.parametrize("expression", ["__import__('os')", "open('x')", "[1,2,3][0]", "1; 2"])
def test_safe_eval_rejects_unsafe_expressions(expression: str) -> None:
    with pytest.raises(UnsafeExpressionError):
        safe_eval(expression)


@pytest.mark.asyncio
async def test_calculator_tool_execute() -> None:
    from app.tools.calculator import CalculatorTool

    result = await CalculatorTool().execute({"expression": "6 * 7"})
    assert result.success
    assert result.output == 42


@pytest.mark.asyncio
async def test_calculator_tool_reports_clean_error_on_bad_expression() -> None:
    from app.tools.calculator import CalculatorTool

    result = await CalculatorTool().execute({"expression": "1 / 0"})
    assert not result.success
    assert result.error


# --- file tools & path safety -------------------------------------------


def test_resolve_within_rejects_traversal(tmp_path) -> None:
    with pytest.raises(PathEscapeError):
        resolve_within(tmp_path, "../outside.txt")


def test_resolve_within_rejects_absolute_path(tmp_path) -> None:
    with pytest.raises(PathEscapeError):
        resolve_within(tmp_path, "/etc/passwd")


def test_resolve_within_allows_nested_relative_path(tmp_path) -> None:
    resolved = resolve_within(tmp_path, "sub/dir/file.txt")
    assert resolved == (tmp_path / "sub" / "dir" / "file.txt").resolve()


@pytest.mark.asyncio
async def test_file_write_then_read_roundtrip(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "generated_dir", str(tmp_path / "generated"))
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path / "generated"))  # read back via same root

    write_result = await FileWriteTool().execute({"path": "note.txt", "content": "hello world"})
    assert write_result.success

    read_result = await FileReadTool().execute({"path": "note.txt", "root": "uploads"})
    assert read_result.success
    assert read_result.output == "hello world"


@pytest.mark.asyncio
async def test_file_read_rejects_path_escape() -> None:
    result = await FileReadTool().execute({"path": "../../etc/passwd", "root": "uploads"})
    assert not result.success
    assert "escapes" in (result.error or "") or "relative" in (result.error or "")


@pytest.mark.asyncio
async def test_file_read_missing_file_reports_clean_error() -> None:
    result = await FileReadTool().execute({"path": "definitely-not-here.txt", "root": "uploads"})
    assert not result.success
    assert "not found" in (result.error or "").lower()
