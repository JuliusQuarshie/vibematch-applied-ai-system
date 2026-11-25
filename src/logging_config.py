"""
Structured logging for VibeMatch 2.0.

Every module gets its logger from get_logger(). Messages are written as an event name
followed by key=value pairs so they are easy to grep, for example:

    2026-11-24 10:00:00 INFO vibematch.agent event=revision_rejected strategy=diversity_rerank reason=...

Privacy note: the pipeline logs which preference fields were supplied and aggregate
metrics, not raw free-text input. Raw values only appear at DEBUG level.
"""

import logging
from typing import Optional

ROOT_LOGGER = "vibematch"
_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Returns a child of the 'vibematch' logger, e.g. get_logger('agent') -> 'vibematch.agent'."""
    return logging.getLogger(f"{ROOT_LOGGER}.{name}")


def configure_logging(level: str = "WARNING", log_file: Optional[str] = None) -> logging.Logger:
    """
    Configures the 'vibematch' logger once. Console output goes to stderr so it never
    mixes with recommendation output on stdout. An optional log file receives the same records.
    Calling it again replaces the previous handlers instead of stacking duplicates.
    """
    numeric = getattr(logging, str(level).upper(), None)
    if not isinstance(numeric, int):
        raise ValueError(f"Unknown log level '{level}'. Use DEBUG, INFO, WARNING or ERROR.")

    logger = logging.getLogger(ROOT_LOGGER)
    logger.setLevel(numeric)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_FORMAT)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = True  # lets pytest's caplog see records
    return logger


def kv(event: str, **fields) -> str:
    """Formats an event and fields as 'event=name key=value ...' with stable key order."""
    parts = [f"event={event}"]
    for key in sorted(fields):
        value = fields[key]
        if isinstance(value, float):
            value = f"{value:.3f}"
        text = str(value)
        if " " in text:
            text = '"' + text.replace('"', "'") + '"'
        parts.append(f"{key}={text}")
    return " ".join(parts)
