from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Self

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from contester.extensions import db
from contester.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from contester.models.user import User


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ContestStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


CONTEST_STATUS_ENUM = Enum(
    ContestStatus,
    name="contest_status",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Contest(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "contests"
    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="contest_schedule_valid",
        ),
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ContestStatus] = mapped_column(
        CONTEST_STATUS_ENUM,
        nullable=False,
        default=ContestStatus.DRAFT,
        index=True,
    )
    created_by_id = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_by: Mapped[User] = relationship(back_populates="created_contests")

    def __repr__(self) -> str:
        return f"Contest(id={self.id!s}, slug={self.slug!r}, status={self.status.value!r})"

    @staticmethod
    def normalize_title(title: str) -> str:
        normalized = title.strip()
        if not normalized:
            raise ValueError("Title must not be empty.")
        if len(normalized) > 160:
            raise ValueError("Title must be at most 160 characters long.")
        return normalized

    @staticmethod
    def normalize_slug(slug: str) -> str:
        normalized = slug.strip().lower()
        if not normalized:
            raise ValueError("Slug must not be empty.")
        if len(normalized) > 80:
            raise ValueError("Slug must be at most 80 characters long.")
        if not SLUG_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Slug must contain only lowercase latin letters, digits, and single hyphens."
            )
        return normalized

    @staticmethod
    def normalize_description(description: str | None) -> str | None:
        if description is None:
            return None

        normalized = description.strip()
        return normalized or None

    @staticmethod
    def normalize_schedule_value(value: datetime | None) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            raise ValueError("Datetime values must include timezone information.")

        return value.astimezone(timezone.utc)

    @classmethod
    def validate_schedule(
        cls,
        *,
        starts_at: datetime | None,
        ends_at: datetime | None,
    ) -> None:
        normalized_starts_at = cls.normalize_schedule_value(starts_at)
        normalized_ends_at = cls.normalize_schedule_value(ends_at)

        if (
            normalized_starts_at is not None
            and normalized_ends_at is not None
            and normalized_ends_at <= normalized_starts_at
        ):
            raise ValueError("Contest end time must be greater than start time.")

    @classmethod
    def create(
        cls,
        *,
        title: str,
        slug: str,
        description: str | None,
        starts_at: datetime | None,
        ends_at: datetime | None,
        status: ContestStatus,
        created_by: User,
    ) -> Self:
        normalized_starts_at = cls.normalize_schedule_value(starts_at)
        normalized_ends_at = cls.normalize_schedule_value(ends_at)
        cls.validate_schedule(starts_at=normalized_starts_at, ends_at=normalized_ends_at)

        return cls(
            title=cls.normalize_title(title),
            slug=cls.normalize_slug(slug),
            description=cls.normalize_description(description),
            starts_at=normalized_starts_at,
            ends_at=normalized_ends_at,
            status=status,
            created_by=created_by,
        )

    def set_title(self, title: str) -> None:
        self.title = self.normalize_title(title)

    def set_slug(self, slug: str) -> None:
        self.slug = self.normalize_slug(slug)

    def set_description(self, description: str | None) -> None:
        self.description = self.normalize_description(description)

    def set_status(self, status: ContestStatus) -> None:
        self.status = status

    def set_schedule(
        self,
        *,
        starts_at: datetime | None,
        ends_at: datetime | None,
    ) -> None:
        normalized_starts_at = self.normalize_schedule_value(starts_at)
        normalized_ends_at = self.normalize_schedule_value(ends_at)
        self.validate_schedule(starts_at=normalized_starts_at, ends_at=normalized_ends_at)
        self.starts_at = normalized_starts_at
        self.ends_at = normalized_ends_at