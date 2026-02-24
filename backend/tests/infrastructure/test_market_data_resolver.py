from domain.protocols import MarketDataProvider
from infrastructure.market_data_resolver import MarketDataResolver


def test_resolver_satisfies_protocol():
    """MarketDataResolver structurally conforms to MarketDataProvider."""
    resolver = MarketDataResolver()
    assert isinstance(resolver, MarketDataProvider)
