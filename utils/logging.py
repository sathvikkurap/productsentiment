"""Structured logging for the crawler."""

import logging
import sys


def get_logger(name: str, verbose: bool = False) -> logging.Logger:
    """Return a logger with Rich-style console handler."""
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    )
    log.addHandler(h)
    return log
