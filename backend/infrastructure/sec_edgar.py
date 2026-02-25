"""Backward-compatibility shim — re-exports infrastructure.external.sec_edgar.

Consumers using ``from infrastructure.sec_edgar import X`` continue to work unchanged.
"""

from infrastructure.external.sec_edgar import (  # noqa: F401
    fetch_13f_filing_detail,
    fetch_company_filings,
    get_latest_13f_filings,
    map_cusip_to_ticker,
)
