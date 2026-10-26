"""Error details for later: a small log file next to the settings.

The window shows people a short message in a dialog; the full traceback goes here, so nothing is
swallowed silently. The file is ~/.csv_plot_studio.log (or the path in CSV_PLOT_STUDIO_LOG),
rotated at 1 MB.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import traceback
from pathlib import Path

_LOGGER: logging.Logger | None = None


def log_path() -> Path:
    return Path(os.environ.get("CSV_PLOT_STUDIO_LOG") or Path.home() / ".csv_plot_studio.log")


def logger() -> logging.Logger:
    """The app's logger, writing to the log file (or to stderr if the file can't be opened)."""
    global _LOGGER
    if _LOGGER is None:
        log = logging.getLogger("plotstudio")
        log.setLevel(logging.INFO)
        log.propagate = False
        try:
            handler: logging.Handler = logging.handlers.RotatingFileHandler(
                log_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        except OSError:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(handler)
        _LOGGER = log
    return _LOGGER


def log_error(what: str, exc: BaseException | None = None, details: str = "") -> str:
    """Write `what` plus the traceback of exc (or `details`) to the log; return the details."""
    if not details and exc is not None:
        details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger().error("%s\n%s", what, details.rstrip())
    return details
