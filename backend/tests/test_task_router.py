"""TaskRouter (Agent Selector): file-type signals, phrase scoring, and the
low-confidence General fallback — plus the /api/chat integration when
`agent_id` is omitted or `"auto"`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.base import AttachmentRef
from app.agents.manager import build_default_agent_manager
from app.agents.task_router import TaskRouter


def _router() -> TaskRouter:
    return TaskRouter(build_default_agent_manager())


def test_code_phrases_route_to_code_agent() -> None:
    result = _router().select("There's a bug in this function, can you find the error?", [])
    assert result.agent_id == "code"
    assert result.confidence > 0
    assert result.reason


def test_document_phrases_route_to_document_agent() -> None:
    result = _router().select("Please summarize this report and draft a memo.", [])
    assert result.agent_id == "document"


def test_data_phrases_route_to_data_agent() -> None:
    result = _router().select("Calculate the average and show statistics for this dataset.", [])
    assert result.agent_id == "data"


def test_vision_phrases_route_to_vision_agent() -> None:
    result = _router().select("Inspect this photograph of the equipment.", [])
    assert result.agent_id == "vision"


def test_image_attachment_routes_to_vision_agent() -> None:
    result = _router().select(
        "What do you see here?", [AttachmentRef(id="a1", filename="pump.jpg")]
    )
    assert result.agent_id == "vision"
    assert result.confidence >= 0.9


def test_csv_attachment_routes_to_data_agent() -> None:
    result = _router().select(
        "Look at this", [AttachmentRef(id="a1", filename="production.csv")]
    )
    assert result.agent_id == "data"


def test_ambiguous_request_falls_back_to_general() -> None:
    result = _router().select("Hello there, how are you today?", [])
    assert result.agent_id == "general"


def test_empty_message_falls_back_to_general_without_crashing() -> None:
    result = _router().select("", [])
    assert result.agent_id == "general"
    assert result.confidence == 0.0


def test_reason_is_plain_sentence_not_internal_detail() -> None:
    result = _router().select("Fix this Python traceback", [])
    assert result.reason == "The request involves code, debugging, or a programming task."
    assert "score" not in result.reason.lower()


# --- /api/chat integration ---------------------------------------------


def test_chat_auto_mode_omitted_agent_id_routes_correctly(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "There's a bug in my python script, please fix the error."})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["agent"]["id"] == "code"
    assert body["task_routing"] is not None
    assert body["task_routing"]["agent_id"] == "code"
    assert body["task_routing"]["reason"]

    selecting_step = next(s for s in body["execution"]["steps"] if s["id"] == "selecting_agent")
    assert selecting_step["detail"] == body["task_routing"]["reason"]


def test_chat_auto_mode_literal_auto_string(client: TestClient) -> None:
    response = client.post("/api/chat", json={"agent_id": "auto", "message": "Calculate the average of this dataset."})
    assert response.status_code == 200
    assert response.json()["agent"]["id"] == "data"


def test_chat_manual_mode_unaffected_by_task_router(client: TestClient) -> None:
    """A concrete agent_id must never be overridden by the Task Router,
    even if the message text would suggest a different agent.
    """
    response = client.post("/api/chat", json={"agent_id": "general", "message": "There's a bug in this code."})
    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["id"] == "general"
    assert body["task_routing"] is None

    selecting_step = next(s for s in body["execution"]["steps"] if s["id"] == "selecting_agent")
    assert selecting_step["detail"] is None


def test_chat_auto_mode_ambiguous_message_uses_general(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "Hi, how are you?"})
    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["id"] == "general"
    assert body["task_routing"]["agent_id"] == "general"
