"""Shared pytest config for the api test suite."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
_REPO = _HERE.parent.parent.parent

for p in (_SRC, _REPO):
    p = str(p)
    if p not in sys.path:
        sys.path.insert(0, p)
