from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.submission import (
    Submission,
    SubmissionLanguage,
    SubmissionStatus,
    SubmissionVerdict,
)
from contester.models.user import User, UserRole
from contester.services import SubmissionQueueService


def _create_user(*, username: str, password: str, role: UserRole) -> User:
    user = User.create(username=username, password=password, role=role)
    db.session.add(user)
    db.session.commit()
    return user


def _create_contest(*, creator: User, title: str, slug: str, status: ContestStatus) -> Contest:
    contest = Contest.create(
        title=title,
        slug=slug,
        description="Contest description",
        starts_at=None,
        ends_at=None,
        status=status,
        created_by=creator,
    )
    db.session.add(contest)
    db.session.commit()
    return contest


def _create_problem(
    *,
    contest: Contest,
    code: str,
    title: str,
    position: int,
    status: ProblemStatus,
) -> Problem:
    problem = Problem.create(
        contest=contest,
        code=code,
        title=title,
        statement="Solve the problem.",
        input_specification="Input spec",
        output_specification="Output spec",
        notes=None,
        sample_input="1 2",
        sample_output="3",
        time_limit_ms=1000,
        memory_limit_mb=128,
        position=position,
        status=status,
    )
    db.session.add(problem)
    db.session.commit()
    return problem


def _create_submission(
    *,
    user: User,
    problem: Problem,
    status: SubmissionStatus,
    verdict: SubmissionVerdict,
    created_at: datetime,
    updated_at: datetime | None = None,
) -> Submission:
    submission = Submission.create(
        user=user,
        problem=problem,
        language=SubmissionLanguage.PYTHON,
        source_code="print('ok')\n",
    )
    db.session.add(submission)
    db.session.flush()

    submission.created_at = created_at
    submission.updated_at = updated_at or created_at
    submission.status = status
    submission.verdict = verdict

    if status == SubmissionStatus.FINISHED:
        submission.passed_test_count = 1 if verdict == SubmissionVerdict.ACCEPTED else 0
        submission.total_test_count = 1
        submission.judged_at = created_at
    else:
        submission.passed_test_count = 0
        submission.total_test_count = 0
        submission.judged_at = None

    db.session.commit()
    return submission


def test_claim_pending_submission_ids_marks_oldest_items_running(app) -> None:
    with app.app_context():
        admin = _create_user(username="admin-queue-batch", password="verystrong123", role=UserRole.ADMIN)
        participant = _create_user(
            username="participant-queue-batch",
            password="verystrong123",
            role=UserRole.PARTICIPANT,
        )
        contest = _create_contest(
            creator=admin,
            title="Queue Contest",
            slug="queue-batch-contest",
            status=ContestStatus.PUBLISHED,
        )
        problem = _create_problem(
            contest=contest,
            code="A",
            title="A + B",
            position=1,
            status=ProblemStatus.PUBLISHED,
        )

        first = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.PENDING,
            verdict=SubmissionVerdict.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=3),
        )
        second = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.PENDING,
            verdict=SubmissionVerdict.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        third = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.PENDING,
            verdict=SubmissionVerdict.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        service = SubmissionQueueService.from_app_config()
        claimed_ids = service.claim_pending_submission_ids(limit=2)

        assert claimed_ids == [first.id, second.id]

        first_reloaded = db.session.get(Submission, first.id)
        second_reloaded = db.session.get(Submission, second.id)
        third_reloaded = db.session.get(Submission, third.id)

        assert first_reloaded is not None
        assert second_reloaded is not None
        assert third_reloaded is not None

        assert first_reloaded.status == SubmissionStatus.RUNNING
        assert second_reloaded.status == SubmissionStatus.RUNNING
        assert third_reloaded.status == SubmissionStatus.PENDING


def test_claim_next_pending_submission_id_marks_oldest_pending_running(app) -> None:
    with app.app_context():
        admin = _create_user(username="admin-queue-claim", password="verystrong123", role=UserRole.ADMIN)
        participant = _create_user(
            username="participant-queue-claim",
            password="verystrong123",
            role=UserRole.PARTICIPANT,
        )
        contest = _create_contest(
            creator=admin,
            title="Queue Contest",
            slug="queue-claim-contest",
            status=ContestStatus.PUBLISHED,
        )
        problem = _create_problem(
            contest=contest,
            code="A",
            title="A + B",
            position=1,
            status=ProblemStatus.PUBLISHED,
        )

        first = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.PENDING,
            verdict=SubmissionVerdict.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        second = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.PENDING,
            verdict=SubmissionVerdict.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        service = SubmissionQueueService.from_app_config()
        claimed_id = service.claim_next_pending_submission_id()

        assert claimed_id == first.id

        first_reloaded = db.session.get(Submission, first.id)
        second_reloaded = db.session.get(Submission, second.id)

        assert first_reloaded is not None
        assert second_reloaded is not None
        assert first_reloaded.status == SubmissionStatus.RUNNING
        assert first_reloaded.verdict == SubmissionVerdict.PENDING
        assert second_reloaded.status == SubmissionStatus.PENDING


def test_requeue_stale_running_submissions_only_requeues_stale_items(app) -> None:
    now = datetime.now(timezone.utc)

    with app.app_context():
        admin = _create_user(username="admin-queue-stale", password="verystrong123", role=UserRole.ADMIN)
        participant = _create_user(
            username="participant-queue-stale",
            password="verystrong123",
            role=UserRole.PARTICIPANT,
        )
        contest = _create_contest(
            creator=admin,
            title="Queue Contest",
            slug="queue-stale-contest",
            status=ContestStatus.PUBLISHED,
        )
        problem = _create_problem(
            contest=contest,
            code="A",
            title="A + B",
            position=1,
            status=ProblemStatus.PUBLISHED,
        )

        stale = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.RUNNING,
            verdict=SubmissionVerdict.PENDING,
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
        )
        fresh = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.RUNNING,
            verdict=SubmissionVerdict.PENDING,
            created_at=now - timedelta(seconds=30),
            updated_at=now - timedelta(seconds=30),
        )

        service = SubmissionQueueService.from_app_config()
        recovered_count = service.requeue_stale_running_submissions(timeout_sec=300)

        assert recovered_count == 1

        stale_reloaded = db.session.get(Submission, stale.id)
        fresh_reloaded = db.session.get(Submission, fresh.id)

        assert stale_reloaded is not None
        assert fresh_reloaded is not None

        assert stale_reloaded.status == SubmissionStatus.PENDING
        assert stale_reloaded.verdict == SubmissionVerdict.PENDING
        assert stale_reloaded.judge_log == "Submission was re-queued after stale running timeout."

        assert fresh_reloaded.status == SubmissionStatus.RUNNING
        assert fresh_reloaded.verdict == SubmissionVerdict.PENDING


def test_run_once_claims_submission_and_calls_judge_service(app) -> None:
    with app.app_context():
        admin = _create_user(username="admin-queue-run-once", password="verystrong123", role=UserRole.ADMIN)
        participant = _create_user(
            username="participant-queue-run-once",
            password="verystrong123",
            role=UserRole.PARTICIPANT,
        )
        contest = _create_contest(
            creator=admin,
            title="Queue Contest",
            slug="queue-run-once-contest",
            status=ContestStatus.PUBLISHED,
        )
        problem = _create_problem(
            contest=contest,
            code="A",
            title="A + B",
            position=1,
            status=ProblemStatus.PUBLISHED,
        )

        pending = _create_submission(
            user=participant,
            problem=problem,
            status=SubmissionStatus.PENDING,
            verdict=SubmissionVerdict.PENDING,
            created_at=datetime.now(timezone.utc),
        )

        service = SubmissionQueueService.from_app_config()

        claimed_ids: list[UUID] = []

        class FakeJudgeService:
            def judge_submission(self, submission_id):
                claimed_ids.append(submission_id)

        service.judge_service = FakeJudgeService()

        processed = service.run_once()

        assert processed == 1
        assert claimed_ids == [pending.id]

        pending_reloaded = db.session.get(Submission, pending.id)
        assert pending_reloaded is not None
        assert pending_reloaded.status == SubmissionStatus.RUNNING