"""
Infrastructure — SEC EDGAR API 適配器。
負責 EDGAR 外部 API 呼叫、速率限制、快取管理。
所有呼叫皆以 try/except 包裹，失敗時回傳結構化降級結果。
含 tenacity 重試機制，針對暫時性網路錯誤自動指數退避重試。
"""

import contextlib
import os
import re
import threading
import time
import xml.etree.ElementTree as ET

import diskcache
import httpx
from cachetools import TTLCache
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from domain.constants import (
    DISK_CACHE_DIR,
    DISK_CACHE_SIZE_LIMIT,
    DISK_GURU_FILING_TTL,
    DISK_KEY_GURU_FILING,
    GURU_FILING_CACHE_MAXSIZE,
    GURU_FILING_CACHE_TTL,
    SEC_EDGAR_ARCHIVES_BASE_URL,
    SEC_EDGAR_BASE_URL,
    SEC_EDGAR_RATE_LIMIT_CPS,
    SEC_EDGAR_REQUEST_TIMEOUT,
    SEC_EDGAR_USER_AGENT,
    YFINANCE_RETRY_ATTEMPTS,
    YFINANCE_RETRY_WAIT_MAX,
    YFINANCE_RETRY_WAIT_MIN,
)
from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Effective User-Agent: env var overrides the placeholder constant.
# SEC policy requires a real contact email.
# ---------------------------------------------------------------------------
_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", SEC_EDGAR_USER_AGENT)

# ---------------------------------------------------------------------------
# Retry Decorator
# ---------------------------------------------------------------------------
_RETRYABLE = (httpx.TransportError, httpx.TimeoutException, OSError)

_edgar_retry = retry(
    stop=stop_after_attempt(YFINANCE_RETRY_ATTEMPTS),
    wait=wait_exponential(min=YFINANCE_RETRY_WAIT_MIN, max=YFINANCE_RETRY_WAIT_MAX),
    retry=retry_if_exception_type(_RETRYABLE),
    reraise=True,
)

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------


class _EdgarRateLimiter:
    """Thread-safe rate limiter for SEC EDGAR (10 req/sec)."""

    def __init__(self, calls_per_second: float = SEC_EDGAR_RATE_LIMIT_CPS) -> None:
        self._min_interval = 1.0 / calls_per_second
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


_rate_limiter = _EdgarRateLimiter()

# ---------------------------------------------------------------------------
# L1 Memory Cache (quarterly data — long TTL)
# ---------------------------------------------------------------------------
_filing_cache: TTLCache = TTLCache(
    maxsize=GURU_FILING_CACHE_MAXSIZE, ttl=GURU_FILING_CACHE_TTL
)

# ---------------------------------------------------------------------------
# L2 Disk Cache
# ---------------------------------------------------------------------------
_disk_cache = diskcache.Cache(DISK_CACHE_DIR, size_limit=DISK_CACHE_SIZE_LIMIT)


def _disk_get(key: str):
    try:
        return _disk_cache.get(key)
    except Exception:
        return None


def _disk_set(key: str, value, ttl: int) -> None:
    with contextlib.suppress(Exception):
        _disk_cache.set(key, value, expire=ttl)


# ---------------------------------------------------------------------------
# Low-level HTTP helpers
# ---------------------------------------------------------------------------


def _get_headers() -> dict[str, str]:
    return {"User-Agent": _USER_AGENT, "Accept-Encoding": "gzip, deflate"}


@_edgar_retry
def _http_get_json(url: str) -> dict:
    """GET a JSON endpoint from EDGAR with rate limiting and retry."""
    _rate_limiter.wait()
    with httpx.Client(timeout=SEC_EDGAR_REQUEST_TIMEOUT) as client:
        resp = client.get(url, headers=_get_headers())
        resp.raise_for_status()
        return resp.json()


@_edgar_retry
def _http_get_text(url: str) -> str:
    """GET a text/XML endpoint from EDGAR with rate limiting and retry."""
    _rate_limiter.wait()
    with httpx.Client(timeout=SEC_EDGAR_REQUEST_TIMEOUT) as client:
        resp = client.get(url, headers=_get_headers())
        resp.raise_for_status()
        return resp.text


def _discover_infotable_filename(accession_path: str, cik: str) -> str | None:
    """
    從 EDGAR filing index.json 動態探索 information table XML 檔名。

    EDGAR 13F filings 的 information table XML 檔名不固定，可能是：
    - infotable.xml
    - 50240.xml (Berkshire 使用的實際檔名)
    - 13f_infotable.xml
    - 其他數字檔名

    策略：取得 index.json，找出所有 .xml 檔案，排除 primary_doc.xml，
    回傳第一個符合的檔名。

    Args:
        accession_path: Accession number without hyphens (e.g. "000119312526054580").
        cik: 10-digit zero-padded CIK (or stripped CIK will be handled).

    Returns:
        Discovered XML filename (without path), or None on any error.
    """
    index_url = (
        f"{SEC_EDGAR_ARCHIVES_BASE_URL}/Archives/edgar/data/"
        f"{cik.lstrip('0')}/{accession_path}/index.json"
    )

    try:
        index_data = _http_get_json(index_url)
        items = index_data.get("directory", {}).get("item", [])

        # Find all .xml files that are NOT primary_doc.xml
        for item in items:
            name = item.get("name", "")
            if name.endswith(".xml") and name != "primary_doc.xml":
                logger.debug(
                    "EDGAR infotable 檔名探索成功：%s → %s", accession_path, name
                )
                return name

        logger.debug("EDGAR index 中找不到 infotable XML：%s", accession_path)
        return None

    except Exception as exc:
        logger.debug("EDGAR infotable 檔名探索失敗：%s, error=%s", accession_path, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_company_filings(cik: str) -> dict:
    """
    取得 EDGAR 公司申報索引 (submissions JSON)。
    結果以 CIK 為 key，L1+L2 雙層快取。

    Args:
        cik: 10-digit zero-padded SEC CIK code.

    Returns:
        EDGAR submissions JSON dict，失敗時回傳 {"error": str}。
    """
    cached = _filing_cache.get(cik)
    if cached is not None:
        logger.debug("EDGAR submissions L1 命中：CIK=%s", cik)
        return cached

    disk_key = f"{DISK_KEY_GURU_FILING}:submissions:{cik}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        logger.debug("EDGAR submissions L2 命中：CIK=%s", cik)
        _filing_cache[cik] = disk_cached
        return disk_cached

    url = f"{SEC_EDGAR_BASE_URL}/submissions/CIK{cik}.json"
    try:
        result = _http_get_json(url)
        _filing_cache[cik] = result
        _disk_set(disk_key, result, DISK_GURU_FILING_TTL)
        logger.debug("EDGAR submissions 已取得並快取：CIK=%s", cik)
        return result
    except Exception as exc:
        logger.warning("EDGAR submissions 取得失敗：CIK=%s, error=%s", cik, exc)
        return {"error": str(exc)}


def get_latest_13f_filings(cik: str, count: int = 2) -> list[dict]:
    """
    從 EDGAR submissions 索引中篩選最新 N 筆 13F-HR 申報。

    Args:
        cik: 10-digit zero-padded SEC CIK code.
        count: 回傳筆數（預設 2，用於季度比對）。

    Returns:
        list of dicts with keys: accession_number, filing_date, report_date,
        primary_doc, filing_url. Empty list on failure.
    """
    submissions = fetch_company_filings(cik)
    if "error" in submissions:
        return []

    try:
        filings = submissions.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        report_dates = filings.get("reportDate", [])
        primary_docs = filings.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form == "13F-HR":
                accession = accessions[i]
                accession_path = accession.replace("-", "")
                filing_url = (
                    f"{SEC_EDGAR_ARCHIVES_BASE_URL}/Archives/edgar/data/"
                    f"{cik.lstrip('0')}/{accession_path}/{primary_docs[i]}"
                )
                results.append(
                    {
                        "accession_number": accession,
                        "accession_path": accession_path,
                        "filing_date": filing_dates[i],
                        "report_date": report_dates[i],
                        "primary_doc": primary_docs[i],
                        "filing_url": filing_url,
                    }
                )
                if len(results) >= count:
                    break

        logger.debug("EDGAR 13F-HR 申報索引取得：CIK=%s, 共 %d 筆", cik, len(results))
        return results

    except Exception as exc:
        logger.warning("EDGAR 13F 索引解析失敗：CIK=%s, error=%s", cik, exc)
        return []


def fetch_13f_filing_detail(accession_number: str, cik: str) -> list[dict]:
    """
    下載並解析 13F information table XML，回傳持倉明細列表。

    Args:
        accession_number: SEC accession number (e.g. "0001067983-24-000006").
        cik: 10-digit zero-padded CIK (used to build the EDGAR archive URL).

    Returns:
        list of dicts with keys: cusip, company_name, value, shares.
        Empty list on parse failure or network error.
    """
    accession_path = accession_number.replace("-", "")

    # Discover the actual XML filename from the filing index
    xml_filename = _discover_infotable_filename(accession_path, cik)
    if xml_filename is None:
        # Fallback to the common default filename
        xml_filename = "infotable.xml"
        logger.debug(
            "EDGAR infotable 檔名探索失敗，使用預設檔名：%s → %s",
            accession_number,
            xml_filename,
        )

    # Filing documents are served by www.sec.gov, not data.sec.gov
    base = f"{SEC_EDGAR_ARCHIVES_BASE_URL}/Archives/edgar/data/{cik.lstrip('0')}/{accession_path}"
    xml_url = f"{base}/{xml_filename}"

    # Include filename in cache key to prevent stale cache when filename changes
    cache_key = f"{DISK_KEY_GURU_FILING}:infotable:{accession_number}:{xml_filename}"
    disk_cached = _disk_get(cache_key)
    if disk_cached is not None:
        logger.debug("EDGAR infotable L2 命中：%s", accession_number)
        return disk_cached

    try:
        xml_text = _http_get_text(xml_url)
        holdings = _parse_13f_xml(xml_text)
        _disk_set(cache_key, holdings, DISK_GURU_FILING_TTL)
        logger.info(
            "EDGAR infotable 解析完成：%s (%s), %d 筆持倉",
            accession_number,
            xml_filename,
            len(holdings),
        )
        return holdings
    except Exception as exc:
        logger.warning("EDGAR infotable 取得失敗：%s, error=%s", accession_number, exc)
        return []


def map_cusip_to_ticker(cusip: str, company_name: str) -> str | None:
    """
    盡力將 CUSIP 轉換為股票代號。

    策略（依優先順序）：
    1. 靜態本地查找表 (_CUSIP_MAP)
    2. 由公司名稱推斷常見代號（有限）
    3. 回傳 None（未來 Phase 可串接 EDGAR company search API）

    Args:
        cusip: 9-character CUSIP identifier.
        company_name: Company name from 13F filing (best-effort hint).

    Returns:
        Ticker symbol string or None if unmappable.
    """
    # Normalize
    cusip = cusip.strip().upper()
    name_upper = company_name.strip().upper()

    # 1. Static lookup table (most reliable, covers top holdings)
    ticker = _CUSIP_MAP.get(cusip)
    if ticker:
        return ticker

    # 2. Name-based heuristic for well-known names
    for fragment, sym in _NAME_HINTS.items():
        if fragment in name_upper:
            return sym

    return None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_13f_xml(xml_text: str) -> list[dict]:
    """
    解析 SEC 13F information table XML，回傳持倉列表。

    EDGAR 13F XML 使用兩種命名空間變體：
    - 新格式 (2013+): ns 'com/xbrl/dim/2011'
    - 舊格式: no namespace

    Returns:
        list of dicts: cusip, company_name, value (thousands USD), shares.
    """
    # Strip namespace declarations to simplify parsing
    xml_clean = xml_text
    for ns_prefix in (
        'xmlns="',
        "xmlns:ns1=",
        "xmlns:xsi=",
        " xsi:schemaLocation=",
    ):
        if ns_prefix in xml_clean:
            # Remove namespace URIs but keep tag names
            xml_clean = re.sub(r'\s*xmlns[^"]*"[^"]*"', "", xml_clean)
            xml_clean = re.sub(r'\s*xsi:schemaLocation="[^"]*"', "", xml_clean)
            break

    # Strip any residual namespace prefixes from tag names (ns1:infoTable → infoTable)
    xml_clean = re.sub(r"<(/?)[\w]+:", r"<\1", xml_clean)

    try:
        root = ET.fromstring(xml_clean)
    except ET.ParseError as exc:
        logger.warning("13F XML 解析失敗：%s", exc)
        return []

    holdings = []
    # Both wrapper tag names used across EDGAR history
    for entry in root.iter("infoTable"):
        try:
            cusip = _xml_text(entry, "cusip")
            company_name = _xml_text(entry, "nameOfIssuer")
            # value is in thousands USD
            value_str = _xml_text(entry, "value")
            # shrsOrPrnAmt contains sshPrnamt (shares) and sshPrnamtType
            sh_node = entry.find("shrsOrPrnAmt")
            shares_str = _xml_text(sh_node, "sshPrnamt") if sh_node is not None else "0"

            if not cusip or not company_name:
                continue

            holdings.append(
                {
                    "cusip": cusip.strip().upper(),
                    "company_name": company_name.strip(),
                    "value": float(value_str or 0),
                    "shares": float(shares_str or 0),
                }
            )
        except Exception as exc:
            logger.debug("13F infoTable 條目解析跳過：%s", exc)
            continue

    return holdings


def _xml_text(node, tag: str) -> str:
    """Safely extract text from an XML child element."""
    if node is None:
        return ""
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _date_to_quarter(date_str: str) -> int:
    """Convert YYYY-MM-DD to quarter number (1–4)."""
    month = int(date_str[5:7])
    return (month - 1) // 3 + 1


# ---------------------------------------------------------------------------
# Static CUSIP → Ticker map (top institutional holdings)
# Sourced from public EDGAR / financial data, periodically updated.
# ---------------------------------------------------------------------------
_CUSIP_MAP: dict[str, str] = {
    # FAANG / Magnificent 7
    "037833100": "AAPL",
    "02079K305": "GOOGL",
    "02079K107": "GOOG",
    "023135106": "AMZN",
    "67066G104": "NVDA",
    "594918104": "MSFT",
    "88160R101": "TSLA",
    "30303M102": "META",
    "44919P508": "NFLX",
    # Financials
    "025816109": "AXP",
    "808513105": "BAC",
    "172967424": "BRK/B",
    "172967101": "BRK/A",
    "46625H100": "JPM",
    "38141G104": "GS",
    "949746101": "WFC",
    "693475105": "PNC",
    "055622104": "BMY",  # Bristol-Myers Squibb
    # Tech / semis
    "459200101": "IBM",
    "11135F101": "BLK",
    "78468R101": "SNOW",
    "832696405": "CRM",
    "90353T100": "UBER",
    "57636Q104": "MA",
    "91680M107": "V",
    "713448108": "PEP",
    "931142103": "WMT",
    "438516106": "HON",
    "369604103": "GE",
    # Healthcare
    "478160104": "JNJ",
    "58933Y105": "MRK",
    "693506107": "PFE",
    "002824100": "ABT",
    "58155Q103": "MDT",
    # Energy
    "30231G102": "XOM",
    "124653109": "CVX",
    # ETFs commonly held by institutions
    "78462F103": "SPY",
    "464287804": "IVV",
    "921943858": "VTI",
}

# Name fragment → ticker heuristics (uppercase match)
_NAME_HINTS: dict[str, str] = {
    "APPLE INC": "AAPL",
    "MICROSOFT CORP": "MSFT",
    "AMAZON COM": "AMZN",
    "ALPHABET INC": "GOOGL",
    "META PLATFORMS": "META",
    "NVIDIA CORP": "NVDA",
    "TESLA INC": "TSLA",
    "NETFLIX INC": "NFLX",
    "BERKSHIRE HATHAWAY": "BRK/B",
    "JPMORGAN CHASE": "JPM",
    "BANK OF AMERICA": "BAC",
    "AMERICAN EXPRESS": "AXP",
    "EXXON MOBIL": "XOM",
    "CHEVRON CORP": "CVX",
    "WALMART INC": "WMT",
    "JOHNSON & JOHNSON": "JNJ",
    "MASTERCARD INC": "MA",
    "VISA INC": "V",
}
