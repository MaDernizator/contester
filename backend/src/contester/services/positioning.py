from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar
from uuid import UUID

from sqlalchemy import select

from contester.extensions import db
from contester.models.problem import Problem
from contester.models.test_case import TestCase


class _PositionedEntity(Protocol):
    id: object
    position: int
    created_at: object | None


T = TypeVar("T", bound=_PositionedEntity)


def _sort_positioned_items(items: Sequence[T]) -> list[T]:
    return sorted(
        items,
        key=lambda item: (
            item.position,
            item.created_at is None,
            item.created_at,
            str(item.id),
        ),
    )


def _normalize_requested_position(
        requested_position: int | None,
        *,
        max_position: int,
) -> int:
    if requested_position is None:
        return max_position

    return max(1, min(requested_position, max_position))


def _rebalance_for_insert(
        items: Sequence[T],
        *,
        requested_position: int | None,
) -> int:
    ordered_items = _sort_positioned_items(items)
    assigned_position = _normalize_requested_position(
        requested_position,
        max_position=len(ordered_items) + 1,
    )

    next_position = 1
    inserted = False

    for item in ordered_items:
        if not inserted and next_position == assigned_position:
            next_position += 1
            inserted = True

        item.position = next_position
        next_position += 1

    return assigned_position


def _rebalance_for_move(
        items: Sequence[T],
        *,
        moving_item: T,
        requested_position: int | None,
) -> int:
    ordered_items = [
        item
        for item in _sort_positioned_items(items)
        if item.id != moving_item.id
    ]

    assigned_position = _normalize_requested_position(
        requested_position,
        max_position=len(ordered_items) + 1,
    )

    ordered_items.insert(assigned_position - 1, moving_item)

    for index, item in enumerate(ordered_items, start=1):
        item.position = index

    return assigned_position


def _get_problem_siblings(contest_id: UUID) -> list[Problem]:
    return db.session.execute(
        select(Problem)
        .where(Problem.contest_id == contest_id)
        .order_by(Problem.position.asc(), Problem.created_at.asc(), Problem.id.asc())
    ).scalars().all()


def _get_test_case_siblings(problem_id: UUID) -> list[TestCase]:
    return db.session.execute(
        select(TestCase)
        .where(TestCase.problem_id == problem_id)
        .order_by(TestCase.position.asc(), TestCase.created_at.asc(), TestCase.id.asc())
    ).scalars().all()


def assign_problem_insert_position(*, contest_id: UUID, requested_position: int | None) -> int:
    siblings = _get_problem_siblings(contest_id)
    return _rebalance_for_insert(siblings, requested_position=requested_position)


def move_problem_to_position(*, problem: Problem, requested_position: int | None) -> int:
    siblings = _get_problem_siblings(problem.contest_id)
    return _rebalance_for_move(
        siblings,
        moving_item=problem,
        requested_position=requested_position,
    )


def assign_test_case_insert_position(*, problem_id: UUID, requested_position: int | None) -> int:
    siblings = _get_test_case_siblings(problem_id)
    return _rebalance_for_insert(siblings, requested_position=requested_position)


def move_test_case_to_position(*, test_case: TestCase, requested_position: int | None) -> int:
    siblings = _get_test_case_siblings(test_case.problem_id)
    return _rebalance_for_move(
        siblings,
        moving_item=test_case,
        requested_position=requested_position,
    )
