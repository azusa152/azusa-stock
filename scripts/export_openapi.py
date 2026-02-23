"""Export the FastAPI OpenAPI spec to a JSON file for frontend codegen.

Usage:
    backend/.venv/bin/python scripts/export_openapi.py

Writes to: frontend-react/src/api/openapi.json
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Set required env vars before importing the backend (avoids path/cache errors)
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LOG_DIR", str(Path(tempfile.gettempdir()) / "folio_logs"))

# Override disk cache to a writable temp dir so diskcache doesn't fail
_tmp_cache = Path(tempfile.gettempdir()) / "folio_yf_cache_codegen"
_tmp_cache.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Patch DISK_CACHE_DIR in constants before any module imports it
import domain.constants as _constants  # noqa: E402

_constants.DISK_CACHE_DIR = str(_tmp_cache)

from main import app  # noqa: E402

output = Path(__file__).resolve().parent.parent / "frontend-react" / "src" / "api" / "openapi.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(app.openapi(), indent=2) + "\n")

print(f"OpenAPI spec exported to {output}")
