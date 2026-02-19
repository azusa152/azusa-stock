"""Tests for stock management routes (CRUD + signals)."""

from domain.entities import Stock
from domain.enums import StockCategory


class TestCreateStock:
    """Tests for POST /ticker."""

    def test_create_stock_should_return_201_equivalent(self, client):
        # Act
        resp = client.post(
            "/ticker",
            json={
                "ticker": "NVDA",
                "category": "Growth",
                "thesis": "AI leader",
                "tags": ["AI", "GPU"],
            },
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "NVDA"
        assert body["category"] == "Growth"
        assert body["is_active"] is True
        assert body["current_tags"] == ["AI", "GPU"]

    def test_create_stock_should_return_409_when_duplicate(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "Duplicate"},
        )

        # Assert
        assert resp.status_code == 409
        body = resp.json()
        assert body["detail"]["error_code"] == "STOCK_ALREADY_EXISTS"

    def test_create_stock_should_return_422_when_missing_fields(self, client):
        # Act
        resp = client.post("/ticker", json={"ticker": "NVDA"})

        # Assert
        assert resp.status_code == 422


class TestListStocks:
    """Tests for GET /stocks."""

    def test_list_stocks_should_return_empty_initially(self, client):
        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_stocks_should_return_added_stocks(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stocks = resp.json()
        assert len(stocks) == 1
        assert stocks[0]["ticker"] == "NVDA"

    def test_list_stocks_should_include_last_scan_signal(self, client):
        # Arrange — newly added stock defaults to NORMAL signal
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stock = resp.json()[0]
        assert "last_scan_signal" in stock
        assert stock["last_scan_signal"] == "NORMAL"

    def test_list_stocks_should_reflect_updated_scan_signal(self, client, db_session):
        # Arrange — seed stock directly via DB to control last_scan_signal precisely.
        # `client` and `db_session` share the same StaticPool connection (see conftest.py),
        # so writes committed here are visible to the TestClient's session.
        db_session.add(
            Stock(
                ticker="SNPS",
                category=StockCategory.MOAT,
                current_thesis="EDA leader",
                last_scan_signal="THESIS_BROKEN",
                is_active=True,
            )
        )
        db_session.commit()

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stock = next(s for s in resp.json() if s["ticker"] == "SNPS")
        assert stock["last_scan_signal"] == "THESIS_BROKEN"


class TestDeactivateStock:
    """Tests for POST /ticker/{ticker}/deactivate."""

    def test_deactivate_should_succeed(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post("/ticker/NVDA/deactivate", json={"reason": "Overvalued"})

        # Assert
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_deactivate_should_return_404_for_unknown_stock(self, client):
        # Act
        resp = client.post("/ticker/UNKNOWN/deactivate", json={"reason": "Test"})

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "STOCK_NOT_FOUND"

    def test_deactivate_should_return_409_when_already_inactive(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )
        client.post("/ticker/NVDA/deactivate", json={"reason": "First deactivation"})

        # Act
        resp = client.post(
            "/ticker/NVDA/deactivate", json={"reason": "Second deactivation"}
        )

        # Assert
        assert resp.status_code == 409
        assert resp.json()["detail"]["error_code"] == "STOCK_ALREADY_INACTIVE"


class TestReactivateStock:
    """Tests for POST /ticker/{ticker}/reactivate."""

    def test_reactivate_should_succeed(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )
        client.post("/ticker/NVDA/deactivate", json={"reason": "Test"})

        # Act
        resp = client.post("/ticker/NVDA/reactivate", json={})

        # Assert
        assert resp.status_code == 200

    def test_reactivate_should_return_409_when_already_active(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post("/ticker/NVDA/reactivate", json={})

        # Assert
        assert resp.status_code == 409
        assert resp.json()["detail"]["error_code"] == "STOCK_ALREADY_ACTIVE"


class TestUpdateCategory:
    """Tests for PATCH /ticker/{ticker}/category."""

    def test_update_category_should_succeed(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.patch("/ticker/NVDA/category", json={"category": "Moat"})

        # Assert
        assert resp.status_code == 200

    def test_update_category_should_return_404_for_unknown_stock(self, client):
        # Act
        resp = client.patch("/ticker/UNKNOWN/category", json={"category": "Moat"})

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "STOCK_NOT_FOUND"

    def test_update_category_should_return_409_when_unchanged(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.patch("/ticker/NVDA/category", json={"category": "Growth"})

        # Assert
        assert resp.status_code == 409
        assert resp.json()["detail"]["error_code"] == "CATEGORY_UNCHANGED"


class TestCreateStockETF:
    """Tests for is_etf field in POST /ticker."""

    def test_create_stock_should_default_is_etf_to_false(self, client):
        # Act — no is_etf provided, mock returns False
        resp = client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Assert
        assert resp.status_code == 200
        assert resp.json()["is_etf"] is False

    def test_create_stock_should_accept_explicit_is_etf_true(self, client):
        # Act — explicitly pass is_etf=True
        resp = client.post(
            "/ticker",
            json={
                "ticker": "VTI",
                "category": "Trend_Setter",
                "thesis": "US Market ETF",
                "is_etf": True,
            },
        )

        # Assert
        assert resp.status_code == 200
        assert resp.json()["is_etf"] is True

    def test_export_should_include_is_etf_field(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={
                "ticker": "VTI",
                "category": "Trend_Setter",
                "thesis": "ETF",
                "is_etf": True,
            },
        )

        # Act
        resp = client.get("/stocks/export")

        # Assert
        assert resp.status_code == 200
        exported = resp.json()
        assert len(exported) == 1
        assert exported[0]["is_etf"] is True

    def test_list_stocks_should_include_is_etf_field(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={
                "ticker": "MSFT",
                "category": "Trend_Setter",
                "thesis": "Cloud",
            },
        )

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stocks = resp.json()
        assert len(stocks) == 1
        assert stocks[0]["is_etf"] is False


class TestGetSummary:
    """Tests for GET /summary."""

    def test_summary_should_return_plain_text(self, client):
        # Act
        resp = client.get("/summary")

        # Assert
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
