"""GLiNER-backed NER. Optional: install with ``uv sync --extra ml`` and set ``GLINER_ENABLED=1``."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.models import EntityCandidate

_logger = logging.getLogger(__name__)
_model: Any = None


def _get_model() -> Any:
    """Lazy-load GLiNER when enabled; never touches a database."""
    global _model
    if _model is not None:
        return _model
    enabled = os.environ.get("GLINER_ENABLED", "").lower() in ("1", "true", "yes")
    if not enabled:
        return None
    try:
        from gliner import GLiNER
    except ImportError:
        _logger.warning(
            "GLINER_ENABLED but gliner is not installed; use: uv sync --extra ml",
        )
        return None
    model_id = os.environ.get("GLINER_MODEL_ID", "urchade/gliner_small-v2.1")
    _logger.info("Loading GLiNER model %s", model_id)
    _model = GLiNER.from_pretrained(model_id)
    return _model


def extract_with_model(text: str, labels: list[str] | None = None) -> list[EntityCandidate]:
    """Run GLiNER when enabled and dependencies are present; otherwise return []."""
    model = _get_model()
    if model is None or not text.strip():
        return []

    label_names = labels if labels else ["person", "organization", "location"]
    try:
        raw = model.predict_entities(text, labels=label_names, threshold=0.35)
    except Exception as exc:  # pragma: no cover - defensive for API drift
        _logger.warning("GLiNER predict_entities failed: %s", exc)
        return []

    out: list[EntityCandidate] = []
    for item in raw:
        if isinstance(item, dict):
            t = item.get("text", "")
            lab = str(item.get("label", "entity"))
            start = int(item.get("start", 0))
            end = int(item.get("end", start))
            score = float(item.get("score", item.get("probability", 0.5)))
        else:
            t = getattr(item, "text", "")
            lab = str(getattr(item, "label", "entity"))
            start = int(getattr(item, "start", 0))
            end = int(getattr(item, "end", start))
            score = float(getattr(item, "score", 0.5))
        out.append(
            EntityCandidate(
                text=t,
                label=lab,
                start=start,
                end=end,
                confidence=min(1.0, max(0.0, score)),
            ),
        )
    return out
