"""Application exception hierarchy and FastAPI error handling.

Every domain error the API can raise is a `WorkbenchError` subclass carrying
a stable `code`, a user-safe `message`, and the HTTP `status_code` to
respond with. Handlers registered here turn these (and unexpected
exceptions) into a single, consistent JSON error shape and make sure no
Python traceback ever reaches the client — full details are logged
server-side instead.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkbenchError(Exception):
    """Base class for all domain errors the API can raise."""

    code = "internal_error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Something went wrong."

    def __init__(self, message: str | None = None, **details: object) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class InvalidRequestError(WorkbenchError):
    code = "invalid_request"
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "The request was invalid."


class AgentNotFoundError(WorkbenchError):
    code = "agent_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Unknown agent."


class ModelNotFoundError(WorkbenchError):
    code = "model_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Unknown model."


class NoSuitableModelError(WorkbenchError):
    code = "no_suitable_model"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "No approved model can currently handle this request."


class ModelUnavailableError(WorkbenchError):
    code = "model_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "The selected model is not currently available."


class AgentExecutionError(WorkbenchError):
    code = "agent_execution_failed"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "The agent failed to complete this request."


class ResourceNotFoundError(WorkbenchError):
    """Generic 404 for resources that aren't a model or an agent — an
    uploaded file, an ingested document, a generated deliverable, a tool.
    """

    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "The requested resource was not found."


class KnowledgeStoreConfigError(WorkbenchError):
    """The local vector store's embedding dimension doesn't match the
    currently configured `EMBEDDING_PROVIDER` — e.g. documents were
    indexed under the mock provider (a different vector size than a real
    embedding model), then `EMBEDDING_PROVIDER` was changed without
    clearing `CHROMA_PATH`. An infrastructure/configuration problem, not a
    bad request — surfaced clearly rather than as a raw 500, and never
    silently treated as "no relevant document found".
    """

    code = "knowledge_store_config_error"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = (
        "The local knowledge store's embedding dimension does not match the "
        "currently configured embedding provider. This usually means documents "
        "were indexed under a different EMBEDDING_PROVIDER. Clear the local "
        "vector store directory (CHROMA_PATH) and re-ingest your documents."
    )


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    """Wires domain and fallback error handlers onto the FastAPI app."""

    @app.exception_handler(WorkbenchError)
    async def handle_workbench_error(request: Request, exc: WorkbenchError) -> JSONResponse:
        logger.warning(
            "request_failed",
            extra={
                "event": "request_failed",
                "code": exc.code,
                "path": request.url.path,
                "details": exc.details,
            },
        )
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(
            "request_validation_failed",
            extra={"event": "request_validation_failed", "path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_body("invalid_request", "The request body did not match the expected shape."),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Full detail (including traceback) is logged server-side only.
        logger.exception("unhandled_exception", extra={"event": "unhandled_exception", "path": request.url.path})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "An unexpected error occurred."),
        )
