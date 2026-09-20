"""CSV/Data Analysis Tool — real, deterministic statistics via pandas.

The whole point of this tool: the LLM explains what a number means, it
never computes the number itself. `execute()` returns structured, actually
-calculated results (mean/median/std/min/max/missing counts, and optional
groupby aggregation) — see `app/agents/data.py` for how DataAgent folds
this into its response.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.tools.base import BaseTool, ToolResult, ToolRisk
from app.tools.fs_utils import PathEscapeError, resolve_within
from app.tools.fs_utils import root_path as _root_path


def _read_table(path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path)
    return pd.read_csv(path)


def _summarize(df: pd.DataFrame) -> dict[str, Any]:
    numeric = df.select_dtypes(include="number")
    stats = {}
    for column in numeric.columns:
        series = numeric[column].dropna()
        stats[column] = {
            "count": int(series.count()),
            "mean": round(float(series.mean()), 4) if not series.empty else None,
            "median": round(float(series.median()), 4) if not series.empty else None,
            "std": round(float(series.std()), 4) if len(series) > 1 else None,
            "min": round(float(series.min()), 4) if not series.empty else None,
            "max": round(float(series.max()), 4) if not series.empty else None,
        }
    missing = {col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().any()}
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "numeric_summary": stats,
        "missing_values": missing,
    }


class CSVAnalysisTool(BaseTool):
    name = "csv_analysis"
    description = "Computes real statistics (mean/median/std/min/max, missing values, optional group-by) over a local CSV/XLSX file."
    capabilities = ["data_analysis", "tabular_reasoning", "statistics"]
    risk = ToolRisk.LOW
    network = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Path relative to `root`."},
                "root": {"type": "string", "enum": ["uploads", "documents", "generated"], "default": "uploads"},
                "group_by": {"type": "string", "description": "Optional column to group by before aggregating."},
                "agg_column": {"type": "string", "description": "Optional numeric column to aggregate when group_by is set."},
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        from app.core.config import get_settings

        settings = get_settings()
        root = input.get("root", "uploads")
        try:
            target = resolve_within(_root_path(settings, root), input.get("path", ""))
        except PathEscapeError as exc:
            return ToolResult(success=False, error=str(exc))

        if not target.exists():
            return ToolResult(success=False, error=f"File not found: {input.get('path')}")
        if target.suffix.lower() not in (".csv", ".xlsx"):
            return ToolResult(success=False, error=f"Unsupported table format: {target.suffix}")

        try:
            df = _read_table(target)
        except Exception as exc:  # noqa: BLE001 - surface any parse failure as a clean tool error
            return ToolResult(success=False, error=f"Could not parse table: {exc}")

        summary = _summarize(df)

        group_by = input.get("group_by")
        agg_column = input.get("agg_column")
        if group_by and agg_column:
            if group_by not in df.columns or agg_column not in df.columns:
                return ToolResult(success=False, error=f"Unknown column(s): {group_by!r}, {agg_column!r}")
            grouped = df.groupby(group_by)[agg_column].agg(["count", "mean", "sum"]).round(4)
            summary["group_by"] = {
                "column": group_by,
                "aggregated_column": agg_column,
                "groups": {str(k): v for k, v in grouped.to_dict(orient="index").items()},
            }

        return ToolResult(success=True, output=summary, metadata={"path": str(target.name)})
