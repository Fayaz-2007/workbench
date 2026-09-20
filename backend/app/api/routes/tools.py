"""GET /api/tools, POST /api/tools/execute.

Every tool is metadata-declared (name, capabilities, risk, network — see
`app/tools/base.py`) so this surface stays inspectable: nothing a tool can
do is hidden from `GET /api/tools`, and `POST /api/tools/execute` can only
ever reach a tool that's actually registered — never an arbitrary host
operation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_tool_registry, record_activity
from app.schemas.tools import ToolExecuteRequest, ToolExecuteResponse, ToolOut
from app.tools.registry import ToolRegistry

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolOut])
def list_tools(registry: ToolRegistry = Depends(get_tool_registry)) -> list[ToolOut]:
    return [ToolOut(**m.model_dump()) for m in registry.list()]


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    payload: ToolExecuteRequest,
    request: Request,
    registry: ToolRegistry = Depends(get_tool_registry),
) -> ToolExecuteResponse:
    tool = registry.get(payload.tool_name)  # raises ToolNotFoundError (404) if unknown
    result = await tool.execute(payload.input)
    record_activity(
        request,
        action=f"Ran tool: {payload.tool_name}",
        resource=payload.tool_name,
        status="success" if result.success else "failure",
    )
    return ToolExecuteResponse(success=result.success, output=result.output, error=result.error, metadata=result.metadata)
