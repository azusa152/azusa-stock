"""
Architecture boundary tests — enforce clean architecture layer dependencies.

Allowed dependency direction:
  domain/     → stdlib only (no application, infrastructure, api)
  application/ → domain, infrastructure, i18n, logging_config
  infrastructure/ → domain, i18n, logging_config (NOT application, api)
  api/        → application, domain, api, i18n, logging_config (NOT infrastructure, except get_session)
"""

import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parent.parent

LAYER_RULES = {
    "domain": {
        "forbidden": ["application", "infrastructure", "api"],
        "note": "Domain must not depend on any outer layer",
    },
    "infrastructure": {
        "forbidden": ["application", "api"],
        "note": "Infrastructure must not depend on application or api",
    },
    "api": {
        "forbidden_modules": [
            "infrastructure.repositories",
            "infrastructure.market_data",
            "infrastructure.notification",
            "infrastructure.crypto",
            "infrastructure.sec_edgar",
        ],
        "allowed_infrastructure": ["infrastructure.database"],
        "note": "API routes may only import get_session from infrastructure.database",
    },
}


def _collect_imports(filepath: Path) -> list[str]:
    """Parse a Python file and return all imported module names."""
    source = filepath.read_text()
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _get_python_files(layer_dir: Path) -> list[Path]:
    """Get all .py files in a layer directory (non-recursive for test files)."""
    if not layer_dir.exists():
        return []
    return sorted(layer_dir.rglob("*.py"))


class TestDomainBoundary:
    """Domain layer must not import from application, infrastructure, or api."""

    @pytest.fixture
    def domain_files(self):
        return _get_python_files(BACKEND_ROOT / "domain")

    def test_no_forbidden_imports(self, domain_files):
        violations = []
        for filepath in domain_files:
            imports = _collect_imports(filepath)
            violations.extend(
                f"{filepath.name}: imports {imp}"
                for imp in imports
                for forbidden in LAYER_RULES["domain"]["forbidden"]
                if imp == forbidden or imp.startswith(f"{forbidden}.")
            )
        assert violations == [], "Domain layer violations:\n" + "\n".join(violations)


class TestInfrastructureBoundary:
    """Infrastructure must not import from application or api."""

    @pytest.fixture
    def infra_files(self):
        return _get_python_files(BACKEND_ROOT / "infrastructure")

    def test_no_forbidden_imports(self, infra_files):
        violations = []
        for filepath in infra_files:
            imports = _collect_imports(filepath)
            violations.extend(
                f"{filepath.name}: imports {imp}"
                for imp in imports
                for forbidden in LAYER_RULES["infrastructure"]["forbidden"]
                if imp == forbidden or imp.startswith(f"{forbidden}.")
            )
        assert violations == [], "Infrastructure layer violations:\n" + "\n".join(
            violations
        )


class TestApiControllerBoundary:
    """API routes may only use infrastructure.database (for get_session)."""

    @pytest.fixture
    def api_files(self):
        return _get_python_files(BACKEND_ROOT / "api")

    def test_no_direct_infrastructure_imports(self, api_files):
        allowed = set(LAYER_RULES["api"]["allowed_infrastructure"])
        violations = [
            f"{filepath.name}: imports {imp}"
            for filepath in api_files
            for imp in _collect_imports(filepath)
            if imp.startswith("infrastructure") and imp not in allowed
        ]
        assert violations == [], "API layer infrastructure violations:\n" + "\n".join(
            violations
        )
