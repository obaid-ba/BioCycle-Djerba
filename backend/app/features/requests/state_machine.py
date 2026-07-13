"""Collection-request lifecycle: the single source of truth for legal transitions.

Keeping the allowed transitions in one declarative table (rather than scattered
`if` checks across the service) means the lifecycle can be reasoned about, tested,
and extended in isolation. The service consults `assert_transition_allowed`
before mutating state; an illegal move raises `ConflictError` → HTTP 409.
"""

from __future__ import annotations

import enum

from app.shared.exceptions import ConflictError


class RequestStatus(str, enum.Enum):
    """Lifecycle states of a collection request.

    String-valued so they serialize cleanly to JSON and persist as readable
    enum values in PostgreSQL.
    """

    PENDING = "pending"          # created; awaiting operator decision (AI may still be scoring)
    AI_FAILED = "ai_failed"      # AI scoring errored; re-triable, operator can still decide
    ACCEPTED = "accepted"        # operator accepted; scheduled for collection
    REJECTED = "rejected"        # operator rejected (terminal)
    ON_THE_WAY = "on_the_way"    # operator en route
    COLLECTED = "collected"      # waste picked up; real weight captured
    COMPLETED = "completed"      # closed out (terminal)


#: Allowed transitions: source status -> set of reachable target statuses.
#: Absent or empty entries are terminal. This is the ONLY place the graph lives.
_TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.PENDING: frozenset(
        {RequestStatus.AI_FAILED, RequestStatus.ACCEPTED, RequestStatus.REJECTED}
    ),
    # An AI failure doesn't block triage: the operator can still accept/reject,
    # or the system can flip it back to PENDING on a successful re-score.
    RequestStatus.AI_FAILED: frozenset(
        {RequestStatus.PENDING, RequestStatus.ACCEPTED, RequestStatus.REJECTED}
    ),
    RequestStatus.ACCEPTED: frozenset({RequestStatus.ON_THE_WAY}),
    RequestStatus.ON_THE_WAY: frozenset({RequestStatus.COLLECTED}),
    RequestStatus.COLLECTED: frozenset({RequestStatus.COMPLETED}),
    RequestStatus.REJECTED: frozenset(),   # terminal
    RequestStatus.COMPLETED: frozenset(),  # terminal
}

#: Terminal states carry no outgoing transitions.
TERMINAL_STATES: frozenset[RequestStatus] = frozenset(
    status for status, targets in _TRANSITIONS.items() if not targets
)


def is_transition_allowed(current: RequestStatus, target: RequestStatus) -> bool:
    """Return whether `current -> target` is a legal lifecycle move."""
    return target in _TRANSITIONS.get(current, frozenset())


def assert_transition_allowed(current: RequestStatus, target: RequestStatus) -> None:
    """Raise `ConflictError` if `current -> target` is not a legal move.

    Called by the service before any status mutation so that controllers never
    need to know the lifecycle rules.
    """
    if not is_transition_allowed(current, target):
        raise ConflictError(
            f"Illegal status transition: '{current.value}' -> '{target.value}'."
        )
