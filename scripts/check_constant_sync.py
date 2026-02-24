"""
Compare key constants between backend and frontend.
Exit 1 if any drift is detected.

Constant groups verified:
  - Stock categories:  CATEGORY_DISPLAY_ORDER  ↔  STOCK_CATEGORIES
  - Radar categories:  CATEGORY_DISPLAY_ORDER (no Cash)  ↔  RADAR_CATEGORIES
  - Category icons:    CATEGORY_ICON  ↔  CATEGORY_ICON_SHORT
  - Supported currencies: SUPPORTED_CURRENCIES  ↔  FX_CURRENCY_OPTIONS
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKEND_CONSTANTS = ROOT / "backend" / "domain" / "constants.py"
FRONTEND_CONSTANTS = ROOT / "frontend-react" / "src" / "lib" / "constants.ts"


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _get_node_name(node: ast.AST) -> str | None:
    """Return the variable name from an Assign or AnnAssign node."""
    if isinstance(node, ast.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _get_node_value(node: ast.AST) -> ast.expr | None:
    """Return the value expression from an Assign or AnnAssign node."""
    if isinstance(node, ast.Assign):
        return node.value
    elif isinstance(node, ast.AnnAssign):
        return node.value
    return None


def extract_python_list(filepath: Path, var_name: str) -> list[str]:
    """Extract a top-level list constant from a Python file using AST."""
    source = filepath.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            _get_node_name(node) == var_name
            and isinstance(_get_node_value(node), ast.List)
        ):
            value = _get_node_value(node)
            assert isinstance(value, ast.List)
            return [
                elt.value
                for elt in value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
    raise ValueError(f"{var_name} not found as a list in {filepath}")


def extract_python_dict(filepath: Path, var_name: str) -> dict[str, str]:
    """Extract a top-level dict[str, str] constant from a Python file using AST."""
    source = filepath.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            _get_node_name(node) == var_name
            and isinstance(_get_node_value(node), ast.Dict)
        ):
            value = _get_node_value(node)
            assert isinstance(value, ast.Dict)
            result = {}
            for k, v in zip(value.keys, value.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                    result[k.value] = v.value
            return result
    raise ValueError(f"{var_name} not found as a dict in {filepath}")


def extract_ts_array(filepath: Path, var_name: str) -> list[str]:
    """Extract a TypeScript array constant (string literals) using regex."""
    source = filepath.read_text()
    # Match: export const VAR_NAME = [ ... ] as const
    pattern = rf"export\s+const\s+{re.escape(var_name)}\s*=\s*\[(.*?)\]"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        raise ValueError(f"{var_name} not found as an array in {filepath}")
    body = match.group(1)
    return re.findall(r'"([^"]+)"', body)


def extract_ts_record(filepath: Path, var_name: str) -> dict[str, str]:
    """Extract a TypeScript Record<string, string> constant using regex."""
    source = filepath.read_text()
    # Match: export const VAR_NAME: Record<...> = { ... }
    pattern = rf"export\s+const\s+{re.escape(var_name)}[^=]*=\s*\{{(.*?)\}}"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        raise ValueError(f"{var_name} not found as a record in {filepath}")
    body = match.group(1)
    # Parse key: "value" pairs
    result = {}
    for pair in re.finditer(r'(\w+)\s*:\s*"([^"]+)"', body):
        result[pair.group(1)] = pair.group(2)
    return result


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_categories() -> list[str]:
    """Verify CATEGORY_DISPLAY_ORDER matches STOCK_CATEGORIES."""
    errors = []
    backend = extract_python_list(BACKEND_CONSTANTS, "CATEGORY_DISPLAY_ORDER")
    frontend = list(extract_ts_array(FRONTEND_CONSTANTS, "STOCK_CATEGORIES"))
    if backend != frontend:
        errors.append(
            f"STOCK_CATEGORIES mismatch:\n"
            f"  backend  CATEGORY_DISPLAY_ORDER: {backend}\n"
            f"  frontend STOCK_CATEGORIES:        {frontend}"
        )
    return errors


def check_radar_categories() -> list[str]:
    """Verify RADAR_CATEGORIES equals CATEGORY_DISPLAY_ORDER minus 'Cash'."""
    errors = []
    backend_all = extract_python_list(BACKEND_CONSTANTS, "CATEGORY_DISPLAY_ORDER")
    backend_radar = [c for c in backend_all if c != "Cash"]
    frontend = list(extract_ts_array(FRONTEND_CONSTANTS, "RADAR_CATEGORIES"))
    if backend_radar != frontend:
        errors.append(
            f"RADAR_CATEGORIES mismatch:\n"
            f"  backend  (CATEGORY_DISPLAY_ORDER - Cash): {backend_radar}\n"
            f"  frontend RADAR_CATEGORIES:                {frontend}"
        )
    return errors


def check_category_icons() -> list[str]:
    """Verify CATEGORY_ICON matches CATEGORY_ICON_SHORT."""
    errors = []
    backend = extract_python_dict(BACKEND_CONSTANTS, "CATEGORY_ICON")
    frontend = extract_ts_record(FRONTEND_CONSTANTS, "CATEGORY_ICON_SHORT")
    if backend != frontend:
        only_backend = {k: v for k, v in backend.items() if frontend.get(k) != v}
        only_frontend = {k: v for k, v in frontend.items() if backend.get(k) != v}
        errors.append(
            f"CATEGORY_ICON mismatch:\n"
            f"  backend-only changes:  {only_backend}\n"
            f"  frontend-only changes: {only_frontend}"
        )
    return errors


def check_currencies() -> list[str]:
    """Verify SUPPORTED_CURRENCIES matches FX_CURRENCY_OPTIONS."""
    errors = []
    backend = extract_python_list(BACKEND_CONSTANTS, "SUPPORTED_CURRENCIES")
    frontend = list(extract_ts_array(FRONTEND_CONSTANTS, "FX_CURRENCY_OPTIONS"))
    if sorted(backend) != sorted(frontend):
        errors.append(
            f"Supported currencies mismatch:\n"
            f"  backend  SUPPORTED_CURRENCIES: {backend}\n"
            f"  frontend FX_CURRENCY_OPTIONS:  {frontend}"
        )
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    errors: list[str] = []
    errors.extend(check_categories())
    errors.extend(check_radar_categories())
    errors.extend(check_category_icons())
    errors.extend(check_currencies())

    if errors:
        print("Constant sync errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Constants in sync.")


if __name__ == "__main__":
    main()
