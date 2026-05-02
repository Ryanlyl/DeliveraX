from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
API_SERVER_ROOT = REPO_ROOT / "ApiServer"

for path in (REPO_ROOT, API_SERVER_ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
