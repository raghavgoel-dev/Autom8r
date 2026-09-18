"""Application logging setup.

One ``get_logger`` helper used everywhere so log format stays consistent.
We log *what happened* (request paths, tool names, durations) and never
secrets — there is no code path here that could print an API key.
"""
import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Attach one stream handler to the root logger (idempotent)."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    # Quiet noisy third parties without hiding real problems.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger with the shared configuration applied."""
    configure_logging()
    return logging.getLogger(name)
