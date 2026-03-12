from __future__ import annotations

from typing import TYPE_CHECKING, Self

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from contester.extensions import db
from contester.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from contester.models.problem import Problem


class TestCase(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "test_cases"
    __table_args__ = (
        CheckConstraint("position >= 1", name="test_case_position_positive"),
    )

    __test__ = False

    problem_id = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    problem: Mapped[Problem] = relationship(back_populates="test_cases")

    def __repr__(self) -> str:
        return (
            f"TestCase(id={self.id!s}, problem_id={self.problem_id!s}, "
            f"position={self.position}, is_active={self.is_active})"
        )

    @staticmethod
    def normalize_required_text(value: str, field_name: str) -> str:
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized.strip():
            raise ValueError(f"{field_name} must not be empty.")
        return normalized

    @staticmethod
    def validate_position(position: int) -> None:
        if position < 1:
            raise ValueError("Test case position must be greater than or equal to 1.")

    @classmethod
    def create(
        cls,
        *,
        problem: Problem,
        position: int,
        input_data: str,
        expected_output: str,
        is_sample: bool = False,
        is_active: bool = True,
    ) -> Self:
        cls.validate_position(position)

        return cls(
            problem=problem,
            position=position,
            input_data=cls.normalize_required_text(input_data, "Input data"),
            expected_output=cls.normalize_required_text(expected_output, "Expected output"),
            is_sample=is_sample,
            is_active=is_active,
        )

    def set_position(self, position: int) -> None:
        self.validate_position(position)
        self.position = position

    def set_input_data(self, input_data: str) -> None:
        self.input_data = self.normalize_required_text(input_data, "Input data")

    def set_expected_output(self, expected_output: str) -> None:
        self.expected_output = self.normalize_required_text(expected_output, "Expected output")