"""Fail-open Langfuse tracing and evaluation score helpers."""

import atexit
import json
import logging
import math
import os
import re
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
_langfuse = None
_callback_handler = None
_initialized = False

_REDACTION_PATTERNS = (
    (re.compile(r"\b(?:sk|pk)-lf-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_LANGFUSE_KEY]"),
    (re.compile(r"\bnvapi-[A-Za-z0-9_-]{8,}\b", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
    (
        re.compile(
            r"(?i)\b(api[_ -]?key|secret(?:[_ -]?key)?|access[_ -]?token|password)"
            r"(\s*[:=]\s*)([^\s,;\"']+)"
        ),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
)


def redact_sensitive_text(value: str) -> str:
    """Redact common API-key forms, labeled credentials, and email addresses."""
    redacted = value
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_attribute(value):
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {key: _redact_attribute(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_redact_attribute(item) for item in value)
    if isinstance(value, list):
        return [_redact_attribute(item) for item in value]
    return value


def _mask_otel_spans(*, params):
    """Mask sensitive strings from both Langfuse and LangChain spans on export."""
    from langfuse.types import MaskOtelSpansResult, OtelSpanPatch

    patches = {}
    for identifier, span in params.spans.items():
        replacements = {}
        for key, value in span.attributes.items():
            masked_value = _redact_attribute(value)
            if masked_value != value:
                replacements[key] = masked_value
        if replacements:
            patches[identifier] = OtelSpanPatch(set_attributes=replacements)

    return MaskOtelSpansResult(span_patches=patches) if patches else None


def configure_observability() -> None:
    """Initialize Langfuse when enabled and credentials are configured."""
    global _langfuse, _callback_handler, _initialized

    if _initialized:
        return
    _initialized = True

    load_dotenv()
    enabled = os.getenv("LANGFUSE_ENABLED", "true").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        logger.info("Langfuse tracing disabled by LANGFUSE_ENABLED.")
        return

    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        logger.info("Langfuse tracing disabled; configure the Langfuse project keys to enable it.")
        return

    try:
        from langfuse import Langfuse, get_client
        from langfuse.langchain import CallbackHandler

        # Initialize the SDK singleton with a pre-export masking hook so
        # LangChain-generated spans receive the same credential/PII scrubbing.
        Langfuse(mask_otel_spans=_mask_otel_spans)
        _langfuse = get_client()
        _callback_handler = CallbackHandler()
        atexit.register(flush_observability)
        logger.info("Langfuse tracing initialized for environment %s.", os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "default"))
    except Exception as exc:
        _langfuse = None
        _callback_handler = None
        logger.warning("Could not initialize Langfuse; continuing without tracing: %s", redact_sensitive_text(str(exc)))


@contextmanager
def observation_span(
    name: str,
    *,
    input_value: object | None = None,
    as_type: str = "span",
    trace_id: str | None = None,
) -> Iterator[object | None]:
    """Create a Langfuse observation; instrumentation errors never stop app work."""
    if _langfuse is None:
        yield None
        return

    context = None
    try:
        trace_context = {"trace_id": trace_id} if trace_id and re.fullmatch(r"[0-9a-f]{32}", trace_id) else None
        context = _langfuse.start_as_current_observation(
            as_type=as_type,
            name=name,
            input=_redact_attribute(input_value),
            trace_context=trace_context,
        )
        span = context.__enter__()
    except Exception as exc:
        logger.warning("Could not start Langfuse observation %s: %s", name, redact_sensitive_text(str(exc)))
        yield None
        return

    try:
        yield span
    except BaseException as exc:
        try:
            context.__exit__(type(exc), exc, exc.__traceback__)
        except Exception as tracing_exc:
            logger.warning("Could not close Langfuse observation %s: %s", name, redact_sensitive_text(str(tracing_exc)))
        raise
    else:
        try:
            context.__exit__(None, None, None)
        except Exception as exc:
            logger.warning("Could not close Langfuse observation %s: %s", name, redact_sensitive_text(str(exc)))


def set_span_output(span: object | None, output: object) -> None:
    """Attach a redacted string or JSON-serializable result to an observation."""
    if span is None:
        return

    value = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, default=str)
    try:
        span.update(output=redact_sensitive_text(value))
    except Exception as exc:
        logger.warning("Could not update Langfuse observation output: %s", redact_sensitive_text(str(exc)))


def set_span_metadata(span: object | None, metadata: dict) -> None:
    """Attach redacted metadata without allowing tracing to interrupt app work."""
    if span is None:
        return
    try:
        span.update(metadata=_redact_attribute(metadata))
    except Exception as exc:
        logger.warning("Could not update Langfuse observation metadata: %s", redact_sensitive_text(str(exc)))


def span_trace_id(span: object | None) -> str | None:
    """Get an observation's trace ID when tracing is active."""
    if span is None:
        return None
    try:
        return span.trace_id
    except Exception as exc:
        logger.warning("Could not read Langfuse trace ID: %s", redact_sensitive_text(str(exc)))
        return None


def valid_trace_id(trace_id: object) -> str | None:
    """Accept Langfuse/OpenTelemetry trace IDs only in their 32-hex format."""
    return trace_id if isinstance(trace_id, str) and re.fullmatch(r"[0-9a-f]{32}", trace_id) else None


def langchain_callbacks() -> list:
    """Return the Langfuse callback handler when tracing is active."""
    return [_callback_handler] if _callback_handler is not None else []


def record_score(*, name: str, value: float, trace_id: str | None, comment: str | None = None) -> bool:
    """Attach a numeric score to a trace; scoring failures remain non-fatal."""
    if _langfuse is None or not trace_id:
        return False
    try:
        score_value = float(value)
        if not math.isfinite(score_value):
            return False
        _langfuse.create_score(
            name=name,
            value=score_value,
            trace_id=trace_id,
            data_type="NUMERIC",
            comment=redact_sensitive_text(comment) if comment else None,
        )
        return True
    except Exception as exc:
        logger.warning("Could not record Langfuse score %s: %s", name, redact_sensitive_text(str(exc)))
        return False


def flush_observability() -> None:
    """Send queued traces and scores before the short-lived CLI exits."""
    if _langfuse is None:
        return
    try:
        _langfuse.flush()
    except Exception as exc:
        logger.warning("Could not flush Langfuse events: %s", redact_sensitive_text(str(exc)))
