from __future__ import annotations

import pytest

from contester.models.user import User, UserRole


def test_user_create_sets_default_role_and_hashes_password() -> None:
    user = User.create(username="alice", password="strongpass123")

    assert user.username == "alice"
    assert user.role == UserRole.PARTICIPANT
    assert user.password_hash != "strongpass123"
    assert user.check_password("strongpass123") is True


def test_user_create_normalizes_optional_fields() -> None:
    user = User.create(
        username="  bob  ",
        password="anotherpass123",
        email="  BOB@Example.com ",
        full_name="  Bob Smith  ",
    )

    assert user.username == "bob"
    assert user.email == "bob@example.com"
    assert user.full_name == "Bob Smith"


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        User.create(username="charlie", password="short")


def test_password_property_is_write_only() -> None:
    user = User.create(username="diana", password="longpassword123")

    with pytest.raises(AttributeError, match="write-only"):
        _ = user.password