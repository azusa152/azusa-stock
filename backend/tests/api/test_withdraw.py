"""
Tests for POST /withdraw — 聰明提款機 (Smart Withdrawal / Liquidity Waterfall)。
"""

from unittest.mock import patch


def _setup_profile_and_holdings(client):
    """共用 setup：建立投資人格 + 持倉。"""
    # 建立投資人格（目標配置）
    client.post(
        "/profiles",
        json={
            "name": "測試配置",
            "config": {"Growth": 30, "Bond": 50, "Cash": 20},
            "home_currency": "USD",
        },
    )
    # 新增持倉：Growth（有獲利）
    client.post(
        "/holdings",
        json={
            "ticker": "NVDA",
            "category": "Growth",
            "quantity": 10,
            "cost_basis": 80.0,
            "currency": "USD",
        },
    )
    # 新增持倉：Bond
    client.post(
        "/holdings",
        json={
            "ticker": "SGOV",
            "category": "Bond",
            "quantity": 50,
            "cost_basis": 100.0,
            "currency": "USD",
        },
    )
    # 新增現金持倉
    client.post(
        "/holdings/cash",
        json={
            "currency": "USD",
            "amount": 5000.0,
        },
    )


# ---------------------------------------------------------------------------
# Happy Path
# ---------------------------------------------------------------------------


class TestWithdrawHappyPath:
    """POST /withdraw 正常流程。"""

    def test_withdraw_should_return_recommendations(self, client):
        # Arrange
        _setup_profile_and_holdings(client)

        # Act — mock exchange rates (all USD, rate=1.0)
        with patch(
            "application.rebalance_service.get_exchange_rates",
            return_value={"USD": 1.0},
        ):
            resp = client.post(
                "/withdraw",
                json={
                    "target_amount": 1000.0,
                    "display_currency": "USD",
                    "notify": False,
                },
            )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_amount"] == 1000.0
        assert body["total_sell_value"] > 0
        assert len(body["recommendations"]) >= 1
        assert body["shortfall"] == 0.0
        assert "message" in body

    def test_withdraw_recommendations_should_have_required_fields(self, client):
        # Arrange
        _setup_profile_and_holdings(client)

        # Act
        with patch(
            "application.rebalance_service.get_exchange_rates",
            return_value={"USD": 1.0},
        ):
            resp = client.post(
                "/withdraw",
                json={
                    "target_amount": 500.0,
                    "display_currency": "USD",
                    "notify": False,
                },
            )

        # Assert
        body = resp.json()
        for rec in body["recommendations"]:
            assert "ticker" in rec
            assert "category" in rec
            assert "quantity_to_sell" in rec
            assert "sell_value" in rec
            assert "reason" in rec
            assert "priority" in rec
            assert rec["priority"] in [1, 2, 3]


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------


class TestWithdrawValidation:
    """POST /withdraw 驗證錯誤。"""

    def test_withdraw_missing_amount_should_return_422(self, client):
        # Act
        resp = client.post(
            "/withdraw",
            json={
                "display_currency": "USD",
            },
        )

        # Assert
        assert resp.status_code == 422

    def test_withdraw_invalid_amount_type_should_return_422(self, client):
        # Act
        resp = client.post(
            "/withdraw",
            json={
                "target_amount": "not_a_number",
                "display_currency": "USD",
            },
        )

        # Assert
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# No Holdings
# ---------------------------------------------------------------------------


class TestWithdrawNoHoldings:
    """POST /withdraw — 無持倉時。"""

    def test_withdraw_no_holdings_should_return_empty_plan(self, client):
        # Arrange — 建立 profile 但不建立 holdings
        client.post(
            "/profiles",
            json={
                "name": "空配置",
                "config": {"Growth": 50, "Bond": 50},
                "home_currency": "USD",
            },
        )

        # Act
        with patch(
            "application.rebalance_service.get_exchange_rates",
            return_value={"USD": 1.0},
        ):
            resp = client.post(
                "/withdraw",
                json={
                    "target_amount": 1000.0,
                    "display_currency": "USD",
                    "notify": False,
                },
            )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["recommendations"] == []
        assert body["shortfall"] == 1000.0


# ---------------------------------------------------------------------------
# No Profile
# ---------------------------------------------------------------------------


class TestWithdrawNoProfile:
    """POST /withdraw — 無投資人格時。"""

    def test_withdraw_no_profile_should_return_404(self, client):
        # Act — 不建立 profile
        resp = client.post(
            "/withdraw",
            json={
                "target_amount": 1000.0,
                "display_currency": "USD",
                "notify": False,
            },
        )

        # Assert
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Webhook Integration
# ---------------------------------------------------------------------------


class TestWebhookWithdraw:
    """POST /webhook action=withdraw。"""

    def test_webhook_withdraw_should_return_success(self, client):
        # Arrange
        _setup_profile_and_holdings(client)

        # Act
        with patch(
            "application.rebalance_service.get_exchange_rates",
            return_value={"USD": 1.0},
        ):
            resp = client.post(
                "/webhook",
                json={
                    "action": "withdraw",
                    "params": {"amount": 500, "currency": "USD"},
                },
            )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert body["data"]["total_sell_value"] > 0

    def test_webhook_withdraw_missing_amount_should_fail(self, client):
        # Act
        resp = client.post(
            "/webhook",
            json={
                "action": "withdraw",
                "params": {},
            },
        )

        # Assert
        body = resp.json()
        assert body["success"] is False
        assert "amount" in body["message"]

    def test_webhook_withdraw_no_profile_should_fail(self, client):
        # Act
        resp = client.post(
            "/webhook",
            json={
                "action": "withdraw",
                "params": {"amount": 1000},
            },
        )

        # Assert
        body = resp.json()
        assert body["success"] is False

    def test_webhook_help_should_include_withdraw(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        body = resp.json()
        assert body["success"] is True
        assert "withdraw" in body["data"]["actions"]
