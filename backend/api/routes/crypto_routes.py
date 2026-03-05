"""
API — Crypto lookup routes.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import CryptoPrice, CryptoSearchResult
from application.portfolio.crypto_service import (
    get_crypto_price_for_ticker,
    search_crypto_coins,
)
from domain.constants import ERROR_INVALID_INPUT, GENERIC_VALIDATION_ERROR
from i18n import get_user_language, t
from infrastructure.database import get_session

router = APIRouter()


@router.get(
    "/crypto/search",
    response_model=list[CryptoSearchResult],
    summary="Search cryptocurrencies by name/symbol",
)
def search_crypto(q: str) -> list[CryptoSearchResult]:
    results = search_crypto_coins(q)
    return [CryptoSearchResult(**item) for item in results]


@router.get(
    "/crypto/price/{ticker}",
    response_model=CryptoPrice,
    summary="Get crypto price by ticker",
)
def get_crypto_price(
    ticker: str,
    coingecko_id: str | None = None,
    session=Depends(get_session),
) -> CryptoPrice:
    # keep same auth/session pattern as other routes
    lang = get_user_language(session)
    result = get_crypto_price_for_ticker(ticker=ticker, coingecko_id=coingecko_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )
    return CryptoPrice(**result)
