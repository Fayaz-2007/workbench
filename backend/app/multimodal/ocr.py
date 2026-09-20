"""OCR — a modular, swappable abstraction for extracting text from images
and scanned PDF pages.

    Image / scanned PDF page
            |
      Preprocessing (grayscale)
            |
           OCR
            |
     Extracted text  -> app/rag ingestion

`TesseractOCRProvider` requires the `tesseract` binary on PATH (not just
the `pytesseract` Python package, which only talks to that binary) — when
it's missing, `health_check()` and every `extract()` call report a clean
"unavailable" result instead of crashing. OCR is never assumed perfect:
results always carry a best-effort `confidence` and an `errors` list
rather than a bare string.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger, log_event

logger = get_logger(__name__)


@dataclass
class OCRResult:
    text: str
    confidence: float | None  # 0..100, None if the provider can't report one
    engine: str
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class OCRProvider(ABC):
    name: str = "base"

    @abstractmethod
    def extract(self, image_path: Path) -> OCRResult:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> tuple[bool, str]:
        raise NotImplementedError


class NullOCRProvider(OCRProvider):
    """Used when `OCR_PROVIDER=none` — always reports unavailable, cleanly."""

    name = "none"

    def extract(self, image_path: Path) -> OCRResult:
        return OCRResult(text="", confidence=None, engine=self.name, errors=["OCR is disabled (OCR_PROVIDER=none)."])

    def health_check(self) -> tuple[bool, str]:
        return False, "OCR is disabled (OCR_PROVIDER=none)."


class TesseractOCRProvider(OCRProvider):
    """Local OCR via Tesseract (through `pytesseract`). Requires the
    `tesseract` binary to be installed on this machine — see
    https://github.com/tesseract-ocr/tesseract. Fully offline either way.
    """

    name = "tesseract"

    def health_check(self) -> tuple[bool, str]:
        try:
            import pytesseract

            version = str(pytesseract.get_tesseract_version())
            return True, f"tesseract {version} available"
        except ImportError:
            return False, "pytesseract is not installed."
        except Exception as exc:  # noqa: BLE001 - pytesseract raises a plain Exception subclass
            return False, f"tesseract binary not found on PATH: {exc}"

    def extract(self, image_path: Path) -> OCRResult:
        healthy, detail = self.health_check()
        if not healthy:
            log_event(logger, "ocr_unavailable", detail=detail)
            return OCRResult(text="", confidence=None, engine=self.name, errors=[detail])

        try:
            import pytesseract
            from PIL import Image

            with Image.open(image_path) as image:
                grayscale = image.convert("L")  # minimal preprocessing
                data = pytesseract.image_to_data(grayscale, output_type=pytesseract.Output.DICT)
        except Exception as exc:  # noqa: BLE001 - surface any decode/OCR failure cleanly
            return OCRResult(text="", confidence=None, engine=self.name, errors=[f"OCR failed: {exc}"])

        words = [w for w in data.get("text", []) if w.strip()]
        confidences = [float(c) for c in data.get("conf", []) if c not in ("-1", -1)]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        text = " ".join(words)
        log_event(logger, "ocr_completed", chars=len(text), confidence=avg_confidence)
        return OCRResult(text=text, confidence=avg_confidence, engine=self.name)


_provider: OCRProvider | None = None


def get_ocr_provider() -> OCRProvider:
    global _provider
    if _provider is not None:
        return _provider

    from app.core.config import get_settings

    settings = get_settings()
    _provider = TesseractOCRProvider() if settings.ocr_provider == "tesseract" else NullOCRProvider()
    return _provider
