from __future__ import annotations

from enum import StrEnum
from typing import Self

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from contester.extensions import db
from contester.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(StrEnum):
    ADMIN = "admin"
    PARTICIPANT = "participant"


USER_ROLE_ENUM = Enum(
    UserRole,
    name="user_role",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class User(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        USER_ROLE_ENUM,
        nullable=False,
        default=UserRole.PARTICIPANT,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    def __repr__(self) -> str:
        return f"User(id={self.id!s}, username={self.username!r}, role={self.role.value!r})"

    @staticmethod
    def _normalize_username(username: str) -> str:
        normalized = username.strip()
        if not normalized:
            raise ValueError("Username must not be empty.")
        if len(normalized) > 32:
            raise ValueError("Username must be at most 32 characters long.")
        return normalized

    @staticmethod
    def _normalize_email(email: str | None) -> str | None:
        if email is None:
            return None

        normalized = email.strip().lower()
        return normalized or None

    @staticmethod
    def _normalize_full_name(full_name: str | None) -> str | None:
        if full_name is None:
            return None

        normalized = full_name.strip()
        return normalized or None

    def set_password(self, raw_password: str) -> None:
        if len(raw_password) < 8:
            raise ValueError("Password must contain at least 8 characters.")

        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def password(self) -> str:
        raise AttributeError("Password is write-only.")

    @classmethod
    def create(
        cls,
        *,
        username: str,
        password: str,
        role: UserRole = UserRole.PARTICIPANT,
        email: str | None = None,
        full_name: str | None = None,
        is_active: bool = True,
    ) -> Self:
        user = cls(
            username=cls._normalize_username(username),
            email=cls._normalize_email(email),
            full_name=cls._normalize_full_name(full_name),
            role=role,
            is_active=is_active,
        )
        user.set_password(password)
        return user