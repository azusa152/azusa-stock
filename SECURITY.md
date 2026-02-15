# Security Policy

## Vulnerability Management

This document tracks security vulnerabilities, their mitigation status, and accepted risks.

### Patched Vulnerabilities ✅

All critical vulnerabilities have been patched to minimum safe versions:

| Package | CVE | Status | Fixed Version |
|---------|-----|--------|---------------|
| cryptography | CVE-2026-26007 | ✅ Patched | 46.0.5 |
| requests | CVE-2024-47081 | ✅ Patched | 2.32.4 |
| starlette | CVE-2025-54121, CVE-2025-62727 | ✅ Patched | ≥0.49.1 |

### Accepted Risks ⚠️

#### CVE-2025-69872: diskcache 5.6.3 (Pickle Deserialization)

**Status:** Accepted risk - No patch available

**Description:** DiskCache uses Python pickle for serialization by default. An attacker with write access to the cache directory can achieve arbitrary code execution when a victim application reads from the cache.

**Risk Assessment:** LOW

**Justification:**
- **Attack Prerequisites:** Requires write access to `/app/data/yf_cache` directory
- **Mitigation 1 - Docker Isolation:** Cache directory runs inside Docker container with non-root `folio` user
- **Mitigation 2 - Filesystem Permissions:** Volume mounted with restricted permissions (Docker volume or bind mount)
- **Mitigation 3 - Limited Attack Surface:** Cache only stores yfinance market data (quotes, dividends, financials) - no user input or sensitive data
- **Mitigation 4 - Container Security:** If attacker has write access to container filesystem, they already have significant compromise and can exploit many other vectors

**Monitoring:**
- CI pipeline ignores CVE-2025-69872 via `pip-audit --ignore-vuln CVE-2025-69872`
- Will upgrade to patched version when available

**Alternative Considered:**
- Switching to JSON/msgpack serialization would require forking diskcache or finding alternative caching library
- Risk vs. effort trade-off favors accepting current risk with mitigations

---

## Reporting a Vulnerability

If you discover a security vulnerability, please report it via GitHub Security Advisories:

1. Navigate to [Security Advisories](../../security/advisories)
2. Click "Report a vulnerability"
3. Provide detailed description, reproduction steps, and impact assessment

**Please do not report security vulnerabilities through public GitHub issues.**

---

## Security Best Practices

For deployment security guidelines, see [Security section in README.md](README.md#安全性-security).
