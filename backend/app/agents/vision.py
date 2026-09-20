"""Vision Agent — image and scanned-document understanding.

When `VISION_MODEL_PROVIDER=ollama` (see `app/core/config.py`) and a
vision-capable Ollama model is registered (`ollama-vision`, see
`app/models/registry.py`), this agent reads any attached image file's
actual bytes off disk and sends them to Ollama's `/api/generate` alongside
the user's prompt via `OllamaVisionProvider` — real image understanding,
never a textual placeholder for the image.

Without that configuration (the default), the Model Router still only has
the metadata-only `vision-small` mock model to offer, so `raw.is_mock` is
always True and this agent returns the same clearly-labeled development
response it always has — it must never claim mock output is real
inference.
"""

from __future__ import annotations

from app.agents.base import AgentTask, AttachmentRef, BaseAgent, ExecutionContext, response_notice
from app.models.base import GenerationResult, ModelInfo, ModelType
from app.tools.fs_utils import PathEscapeError, resolve_within

_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}


def _is_image_attachment(attachment: AttachmentRef) -> bool:
    if "." not in attachment.filename:
        return False
    return attachment.filename.rsplit(".", 1)[-1].lower() in _IMAGE_EXTENSIONS


def _image_attachments(task: AgentTask) -> list[AttachmentRef]:
    return [a for a in task.attachments if _is_image_attachment(a)]


class VisionAgent(BaseAgent):
    id = "vision"
    name = "Vision Agent"
    description = "Image and scanned-document understanding."
    capabilities = ["image_understanding", "multimodal", "visual_reasoning"]
    model_type = ModelType.VISION

    async def build_prompt(self, task: AgentTask, context: ExecutionContext) -> str:
        return (
            "You are a vision assistant. Describe or answer questions about "
            f"the attached image(s).\n\nUser: {task.message}"
        )

    async def resolve_images(self, task: AgentTask, context: ExecutionContext) -> list[bytes]:
        settings = context.settings
        if settings is None:
            return []

        images: list[bytes] = []
        for attachment in _image_attachments(task):
            if not attachment.path:
                continue
            try:
                resolved = resolve_within(settings.upload_path, attachment.path)
            except PathEscapeError:
                continue
            if resolved.exists() and resolved.is_file():
                images.append(resolved.read_bytes())
        return images

    def format_response(self, task: AgentTask, model: ModelInfo, raw: GenerationResult) -> str:
        has_image = bool(_image_attachments(task))
        image_note = (
            f" ({len(task.attachments)} image/file attachment(s) noted, not yet processed)"
            if task.attachments
            else " (no image attached)"
        )
        # Mock path: no vision-capable model is registered
        # (`VISION_MODEL_PROVIDER` is not "ollama"), so `raw.is_mock` is
        # always True here. Once a real vision model is registered, this
        # only takes the real-inference branch below when `raw.is_mock` is
        # actually False — never fabricated.
        if raw.is_mock:
            return (
                f"**Vision Agent** ({model.name})\n\n"
                f"{response_notice(model, raw)}\n\n"
                f"Request received{image_note}:\n\n> {task.message.strip() or '(empty message)'}\n\n"
                "Real image/scanned-document understanding is not implemented yet — "
                "this agent only demonstrates that Vision requests route to a "
                "multimodal-capable model.\n\n"
                f"Routed model output:\n\n{raw.text}"
            )

        header = f"**Vision Agent** ({model.name})"
        if not has_image:
            # Real vision model, but nothing image-shaped was attached — it
            # answered as a plain text chat. Say so plainly rather than
            # letting the reader assume the image was understood.
            return (
                f"{header}\n\n_No image attachment was found on this request — answered as text-only._\n\n"
                f"{raw.text}\n\n---\n{response_notice(model, raw)}"
            )
        return f"{header}\n\n{raw.text}\n\n---\n{response_notice(model, raw)}"
