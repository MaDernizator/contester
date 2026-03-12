from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Self

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from contester.extensions import db
from contester.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from contester.models.problem import Problem
    from contester.models.user import User


class SubmissionLanguage(StrEnum):
    PYTHON = "python"


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"


class SubmissionVerdict(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    INTERNAL_ERROR = "internal_error"
    NO_TESTS = "no_tests"


SUBMISSION_LANGUAGE_ENUM = Enum(
    SubmissionLanguage,
    name="submission_language",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

SUBMISSION_STATUS_ENUM = Enum(
    SubmissionStatus,
    name="submission_status",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

SUBMISSION_VERDICT_ENUM = Enum(
    SubmissionVerdict,
    name="submission_verdict",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Submission(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "submissions"

    user_id = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[SubmissionLanguage] = mapped_column(
        SUBMISSION_LANGUAGE_ENUM,
        nullable=False,
        index=True,
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        SUBMISSION_STATUS_ENUM,
        nullable=False,
        default=SubmissionStatus.PENDING,
        index=True,
    )
    verdict: Mapped[SubmissionVerdict] = mapped_column(
        SUBMISSION_VERDICT_ENUM,
        nullable=False,
        default=SubmissionVerdict.PENDING,
        index=True,
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    passed_test_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_test_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_test_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    judged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="submissions")
    problem: Mapped[Problem] = relationship(back_populates="submissions")

    def __repr__(self) -> str:
        return (
            f"Submission(id={self.id!s}, user_id={self.user_id!s}, problem_id={self.problem_id!s}, "
            f"language={self.language.value!r}, verdict={self.verdict.value!r})"
        )

    @staticmethod
    def normalize_source_code(source_code: str) -> str:
        normalized = source_code.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized.strip():
            raise ValueError("Source code must not be empty.")
        return normalized

    @classmethod
    def create(
        cls,
        *,
        user: User,
        problem: Problem,
        language: SubmissionLanguage,
        source_code: str,
    ) -> Self:
        return cls(
            user=user,
            problem=problem,
            language=language,
            status=SubmissionStatus.PENDING,
            verdict=SubmissionVerdict.PENDING,
            source_code=cls.normalize_source_code(source_code),
            passed_test_count=0,
            total_test_count=0,
        )

    def mark_running(self, *, total_test_count: int) -> None:
        self.status = SubmissionStatus.RUNNING
        self.verdict = SubmissionVerdict.PENDING
        self.total_test_count = total_test_count
        self.passed_test_count = 0
        self.failed_test_position = None
        self.execution_time_ms = None
        self.judge_log = None
        self.judged_at = None

    def finish(
        self,
        *,
        verdict: SubmissionVerdict,
        passed_test_count: int,
        total_test_count: int,
        failed_test_position: int | None = None,
        execution_time_ms: int | None = None,
        judge_log: str | None = None,
    ) -> None:
        self.status = SubmissionStatus.FINISHED
        self.verdict = verdict
        self.passed_test_count = passed_test_count
        self.total_test_count = total_test_count
        self.failed_test_position = failed_test_position
        self.execution_time_ms = execution_time_ms
        self.judge_log = judge_log
        self.judged_at = utc_now()