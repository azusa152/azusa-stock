"""
Verify that every non-infrastructure GitHub CI job has a corresponding
Makefile target that is reachable from `make ci`.

Exit 1 if any CI job is uncovered — forcing the developer to either:
  1. Add the job ID to KNOWN_JOB_MAP with a make target and wire it into `make ci`, OR
  2. Add it to SKIP_JOBS if it is infrastructure-only (no local equivalent needed).

Keys in KNOWN_JOB_MAP are **job IDs** (the YAML key in ci.yml, e.g. "test", "api-spec")
— NOT the human-readable `name:` field, which can change without affecting job identity.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CI_YAML = ROOT / ".github" / "workflows" / "ci.yml"
MAKEFILE = ROOT / "Makefile"

# ---------------------------------------------------------------------------
# Contract: GitHub CI job ID → Makefile target reachable from `make ci`
# ---------------------------------------------------------------------------

KNOWN_JOB_MAP: dict[str, str] = {
    "test": "backend-test",
    "lint": "backend-lint",
    "api-spec": "check-api-spec",
    "frontend-lint": "frontend-lint",
    "frontend-build": "frontend-build",
    "frontend-test": "frontend-test",
    "frontend-security": "frontend-security",
    "constant-sync": "check-constants",
    "locale-parity": "check-i18n",
    "security": "backend-security",
}

# Infrastructure-only jobs — path filtering, meta-checks, etc.
# These have no meaningful local equivalent and do not need a make target.
SKIP_JOBS: set[str] = {"changes", "ci-completeness", "ci-gate"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_ci_job_ids() -> list[str]:
    """Return all job IDs (yaml keys) from ci.yml."""
    with CI_YAML.open() as f:
        data = yaml.safe_load(f)
    return list(data.get("jobs", {}).keys())


def get_makefile_dependencies(target: str) -> set[str]:
    """
    Recursively resolve all make targets reachable from `target`.
    Parses prerequisite lines of the form:  target: dep1 dep2 ...
    """
    makefile_text = MAKEFILE.read_text()
    dep_map: dict[str, list[str]] = {}

    for line in makefile_text.splitlines():
        if line.startswith("\t") or line.startswith("#") or not line.strip():
            continue
        if ":" in line and not line.startswith(" "):
            lhs, _, rhs = line.partition(":")
            # Skip variable assignments and pattern rules
            if "=" in lhs or "%" in lhs:
                continue
            t = lhs.strip()
            deps = [d for d in rhs.split() if not d.startswith("#") and d != "##"]
            if t:
                dep_map.setdefault(t, []).extend(deps)

    visited: set[str] = set()

    def _walk(t: str) -> None:
        if t in visited:
            return
        visited.add(t)
        for dep in dep_map.get(t, []):
            _walk(dep)

    _walk(target)
    return visited


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not CI_YAML.exists():
        print(f"ERROR: CI workflow not found: {CI_YAML}")
        sys.exit(1)
    if not MAKEFILE.exists():
        print(f"ERROR: Makefile not found: {MAKEFILE}")
        sys.exit(1)

    ci_jobs = get_ci_job_ids()
    ci_targets = get_makefile_dependencies("ci")

    errors: list[str] = []

    for job_id in ci_jobs:
        if job_id in SKIP_JOBS:
            continue
        if job_id not in KNOWN_JOB_MAP:
            errors.append(
                f"  CI job '{job_id}' is not in KNOWN_JOB_MAP or SKIP_JOBS.\n"
                f"  → Add it to KNOWN_JOB_MAP with a make target, or to SKIP_JOBS "
                f"if it is infrastructure-only."
            )
            continue
        make_target = KNOWN_JOB_MAP[job_id]
        if make_target not in ci_targets:
            errors.append(
                f"  CI job '{job_id}' maps to make target '{make_target}', "
                f"but '{make_target}' is not reachable from `make ci`.\n"
                f"  → Add '{make_target}' as a dependency of the `ci` target in Makefile."
            )

    # Also warn if KNOWN_JOB_MAP references a CI job that no longer exists
    known_job_ids = set(KNOWN_JOB_MAP.keys())
    removed_jobs = known_job_ids - set(ci_jobs)
    for job_id in sorted(removed_jobs):
        errors.append(
            f"  KNOWN_JOB_MAP entry '{job_id}' does not match any job in ci.yml.\n"
            f"  → Remove it from KNOWN_JOB_MAP or rename to match the current job ID."
        )

    if errors:
        print("CI completeness check FAILED:")
        for e in errors:
            print(e)
        sys.exit(1)

    print(
        f"CI completeness check passed — all {len(KNOWN_JOB_MAP)} CI jobs "
        f"are covered by `make ci`."
    )


if __name__ == "__main__":
    main()
