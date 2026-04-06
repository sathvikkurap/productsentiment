"""Thin wrapper so the 'productreviews' console script can invoke run.main."""

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from run import main as _run_main  # noqa: PLC0415

    _run_main()
