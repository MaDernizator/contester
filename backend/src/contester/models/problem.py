from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING, Self

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from contester.extensions import db
from contester.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from contester.models.contest import Contest

PROBLEM_CODE_PATTERN = re.compile(r"^[A-Z0-9]+(?:[-_][A-Z0-9]+)*$")


class ProblemStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


PROBLEM_STATUS_ENUM = Enum(
    ProblemStatus,
    name="problem_status",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Problem(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint("position >= 1", name="problem_position_positive"),
        CheckConstraint("time_limit_ms >= 100", name="problem_time_limit_valid"),
        CheckConstraint("memory_limit_mb >= 16", name="problem_memory_limit_valid"),
    )

    contest_id = mapped_column(
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    input_specification: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_specification: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=256)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ProblemStatus] = mapped_column(
        PROBLEM_STATUS_ENUM,
        nullable=False,
        default=ProblemStatus.DRAFT,
        index=True,
    )

    contest: Mapped[Contest] = relationship(back_populates="problems")

    def __repr__(self) -> str:
        return (
            f"Problem(id={self.id!s}, contest_id={self.contest_id!s}, "
            f"code={self.code!r}, status={self.status.value!r})"
        )

    @staticmethod
    def normalize_code(code: str) -> str:
        normalized = code.strip().upper()
        if not normalized:
            raise ValueError("Problem code must not be empty.")
        if len(normalized) > 32:
            raise ValueError("Problem code must be at most 32 characters long.")
        if not PROBLEM_CODE_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Problem code must contain only latin letters, digits, hyphens, and underscores."
            )
        return normalized

    @staticmethod
    def normalize_title(title: str) -> str:
        normalized = title.strip()
        if not normalized:
            raise ValueError("Problem title must not be empty.")
        if len(normalized) > 160:
            raise ValueError("Problem title must be at most 160 characters long.")
        return normalized

    @staticmethod
    def normalize_required_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be empty.")
        return normalized

    @staticmethod
    def normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def validate_limits(*, time_limit_ms: int, memory_limit_mb: int) -> None:
        if time_limit_ms < 100:
            raise ValueError("Time limit must be at least 100 ms.")
        if memory_limit_mb < 16:
            raise ValueError("Memory limit must be at least 16 MB.")

    @staticmethod
    def validate_position(position: int) -> None:
        if position < 1:
            raise ValueError("Problem position must be greater than or equal to 1.")

    @classmethod
    def create(
            cls,
            *,
            contest: Contest,
            code: str,
            title: str,
            statement: str,
            input_specification: str | None,
            output_specification: str | None,
            notes: str | None,
            sample_input: str | None,
            sample_output: str | None,
            time_limit_ms: int,
            memory_limit_mb: int,
            position: int,
            status: ProblemStatus,
    ) -> Self:
        cls.validate_limits(time_limit_ms=time_limit_ms, memory_limit_mb=memory_limit_mb)
        cls.validate_position(position)

        return cls(
            contest=contest,
            code=cls.normalize_code(code),
            title=cls.normalize_title(title),
            statement=cls.normalize_required_text(statement, "Statement"),
            input_specification=cls.normalize_optional_text(input_specification),
            output_specification=cls.normalize_optional_text(output_specification),
            notes=cls.normalize_optional_text(notes),
            sample_input=cls.normalize_optional_text(sample_input),
            sample_output=cls.normalize_optional_text(sample_output),
            time_limit_ms=time_limit_ms,
            memory_limit_mb=memory_limit_mb,
            position=position,
            status=status,
        )

    def set_code(self, code: str) -> None:
        self.code = self.normalize_code(code)

    def set_title(self, title: str) -> None:
        self.title = self.normalize_title(title)

    def set_statement(self, statement: str) -> None:
        self.statement = self.normalize_required_text(statement, "Statement")

    def set_input_specification(self, value: str | None) -> None:
        self.input_specification = self.normalize_optional_text(value)

    def set_output_specification(self, value: str | None) -> None:
        self.output_specification = self.normalize_optional_text(value)

    def set_notes(self, value: str | None) -> None:
        self.notes = self.normalize_optional_text(value)

    def set_sample_input(self, value: str | None) -> None:
        self.sample_input = self.normalize_optional_text(value)

    def set_sample_output(self, value: str | None) -> None:
        self.sample_output = self.normalize_optional_text(value)

    def set_limits(self, *, time_limit_ms: int, memory_limit_mb: int) -> None:
        self.validate_limits(time_limit_ms=time_limit_ms, memory_limit_mb=memory_limit_mb)
        self.time_limit_ms = time_limit_ms
        self.memory_limit_mb = memory_limit_mb

    def set_position(self, position: int) -> None:
        self.validate_position(position)
        self.position = position

    def set_status(self, status: ProblemStatus) -> None:
        self.status = status
