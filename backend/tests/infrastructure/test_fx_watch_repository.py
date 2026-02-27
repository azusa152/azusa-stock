"""Tests for FX Watch repository functions."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from domain.constants import DEFAULT_USER_ID
from domain.entities import FXWatchConfig
from infrastructure.repositories import (
    create_fx_watch,
    delete_fx_watch,
    find_active_fx_watches,
    find_all_fx_watches,
    find_fx_watch_by_id,
    update_fx_watch,
    update_fx_watch_last_alerted,
)


@pytest.fixture
def test_session() -> Iterator[Session]:
    """Provide a test session (uses conftest's test_engine)."""
    from tests.conftest import test_engine

    with Session(test_engine) as session:
        yield session


class TestFXWatchRepository:
    """Tests for FX Watch repository CRUD operations."""

    def test_create_fx_watch(self, test_session: Session):
        # Arrange
        watch = FXWatchConfig(
            user_id=DEFAULT_USER_ID,
            base_currency="USD",
            quote_currency="TWD",
            recent_high_days=30,
            consecutive_increase_days=3,
            reminder_interval_hours=24,
            is_active=True,
        )

        # Act
        created = create_fx_watch(test_session, watch)

        # Assert
        assert created.id is not None
        assert created.base_currency == "USD"
        assert created.quote_currency == "TWD"
        assert created.is_active is True

    def test_find_fx_watch_by_id(self, test_session: Session):
        # Arrange
        watch = FXWatchConfig(
            user_id=DEFAULT_USER_ID,
            base_currency="USD",
            quote_currency="TWD",
        )
        created = create_fx_watch(test_session, watch)

        # Act
        found = find_fx_watch_by_id(test_session, created.id)

        # Assert
        assert found is not None
        assert found.id == created.id
        assert found.base_currency == "USD"

    def test_find_fx_watch_by_id_returns_none_when_not_found(
        self, test_session: Session
    ):
        # Act
        found = find_fx_watch_by_id(test_session, 9999)

        # Assert
        assert found is None

    def test_find_active_fx_watches(self, test_session: Session):
        # Arrange: create two active and one inactive
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id=DEFAULT_USER_ID,
                base_currency="USD",
                quote_currency="TWD",
                is_active=True,
            ),
        )
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id=DEFAULT_USER_ID,
                base_currency="EUR",
                quote_currency="TWD",
                is_active=True,
            ),
        )
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id=DEFAULT_USER_ID,
                base_currency="JPY",
                quote_currency="TWD",
                is_active=False,
            ),
        )

        # Act
        active_watches = find_active_fx_watches(test_session)

        # Assert
        assert len(active_watches) == 2
        assert all(w.is_active for w in active_watches)

    def test_find_all_fx_watches(self, test_session: Session):
        # Arrange
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id=DEFAULT_USER_ID,
                base_currency="USD",
                quote_currency="TWD",
                is_active=True,
            ),
        )
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id=DEFAULT_USER_ID,
                base_currency="EUR",
                quote_currency="TWD",
                is_active=False,
            ),
        )

        # Act
        all_watches = find_all_fx_watches(test_session)

        # Assert
        assert len(all_watches) == 2

    def test_find_active_fx_watches_filters_by_user_id(self, test_session: Session):
        # Arrange: create watches for different users
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id="user1",
                base_currency="USD",
                quote_currency="TWD",
                is_active=True,
            ),
        )
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id="user2",
                base_currency="EUR",
                quote_currency="TWD",
                is_active=True,
            ),
        )

        # Act
        user1_watches = find_active_fx_watches(test_session, user_id="user1")

        # Assert
        assert len(user1_watches) == 1
        assert user1_watches[0].user_id == "user1"
        assert user1_watches[0].base_currency == "USD"

    def test_update_fx_watch_last_alerted(self, test_session: Session):
        # Arrange
        watch = FXWatchConfig(
            user_id=DEFAULT_USER_ID,
            base_currency="USD",
            quote_currency="TWD",
            last_alerted_at=None,
        )
        created = create_fx_watch(test_session, watch)
        assert created.last_alerted_at is None

        # Act
        now = datetime.now(UTC)
        update_fx_watch_last_alerted(test_session, created.id, now)

        # Assert
        updated = find_fx_watch_by_id(test_session, created.id)
        assert updated is not None
        assert updated.last_alerted_at is not None
        # Ensure both datetimes are timezone-aware for comparison
        updated_time = (
            updated.last_alerted_at.replace(tzinfo=UTC)
            if updated.last_alerted_at.tzinfo is None
            else updated.last_alerted_at
        )
        # Allow small time difference due to processing
        assert abs((updated_time - now).total_seconds()) < 2

    def test_update_fx_watch_last_alerted_does_nothing_when_not_found(
        self, test_session: Session
    ):
        # Act & Assert (should not raise)
        update_fx_watch_last_alerted(test_session, 9999, datetime.now(UTC))

    def test_update_fx_watch_should_persist_changes_and_update_timestamp(
        self, test_session: Session
    ):
        # Arrange
        watch = FXWatchConfig(
            user_id=DEFAULT_USER_ID,
            base_currency="USD",
            quote_currency="TWD",
            recent_high_days=30,
        )
        created = create_fx_watch(test_session, watch)
        original_updated = created.updated_at

        # Act
        created.recent_high_days = 60
        updated = update_fx_watch(test_session, created)

        # Assert
        assert updated.recent_high_days == 60
        found = find_fx_watch_by_id(test_session, created.id)
        assert found is not None
        assert found.recent_high_days == 60
        # updated_at should have changed
        assert found.updated_at is not None
        if original_updated is not None:
            assert found.updated_at >= original_updated

    def test_find_all_fx_watches_should_filter_by_user_id(self, test_session: Session):
        # Arrange: create watches for different users
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id="user_a",
                base_currency="USD",
                quote_currency="TWD",
                is_active=True,
            ),
        )
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id="user_b",
                base_currency="EUR",
                quote_currency="TWD",
                is_active=True,
            ),
        )
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id="user_a",
                base_currency="GBP",
                quote_currency="TWD",
                is_active=False,
            ),
        )

        # Act
        user_a_watches = find_all_fx_watches(test_session, user_id="user_a")

        # Assert
        assert len(user_a_watches) == 2
        assert all(w.user_id == "user_a" for w in user_a_watches)

    def test_find_all_fx_watches_should_return_all_when_user_id_is_none(
        self, test_session: Session
    ):
        # Arrange
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id="user_x",
                base_currency="USD",
                quote_currency="TWD",
            ),
        )
        create_fx_watch(
            test_session,
            FXWatchConfig(
                user_id="user_y",
                base_currency="EUR",
                quote_currency="TWD",
            ),
        )

        # Act
        all_watches = find_all_fx_watches(test_session, user_id=None)

        # Assert
        assert len(all_watches) == 2

    def test_delete_fx_watch(self, test_session: Session):
        # Arrange
        watch = FXWatchConfig(
            user_id=DEFAULT_USER_ID,
            base_currency="USD",
            quote_currency="TWD",
        )
        created = create_fx_watch(test_session, watch)

        # Act
        delete_fx_watch(test_session, created)

        # Assert
        found = find_fx_watch_by_id(test_session, created.id)
        assert found is None
