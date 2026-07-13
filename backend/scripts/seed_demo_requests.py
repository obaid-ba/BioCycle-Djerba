"""Idempotently seed a demo hotel manager, their hotel, and a spread of
collection requests across the lifecycle — so the /requests UI has something to
click through immediately (hotel history + operator queue).

Run after migrations:  python -m scripts.seed_demo_requests

Credentials created (dev only):
    manager@biocycle.dev / changeme123   (role: hotel_manager)
    operator@biocycle.dev / changeme123  (role: operator)

Safe to re-run: users/hotel are matched by email/name; requests are only seeded
if the demo hotel currently has none.
"""

import asyncio

import app.models_metadata  # noqa: F401 — register all models so FKs resolve
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.features.auth.models import User, UserRole
from app.features.hotels.models import Hotel, HotelStatus
from app.features.requests.models import CollectionRequest
from app.features.requests.repository import RequestRepository
from app.features.requests.schemas import (
    CollectionRequestCreate,
    RequestDecision,
    RequestTransition,
)
from app.features.requests.service import RequestService
from app.features.requests.state_machine import RequestStatus

MANAGER_EMAIL = "manager@biocycle.dev"
OPERATOR_EMAIL = "operator@biocycle.dev"
PASSWORD = "changeme123"
HOTEL_NAME = "Demo Beach Resort"

# (declared_kg, how far to advance the request through its lifecycle)
DEMO_REQUESTS: list[tuple[float, str]] = [
    (120.0, "pending"),      # awaiting operator decision
    (480.0, "pending"),      # big load, should rank high in the queue
    (60.0, "rejected"),      # operator rejected
    (300.0, "accepted"),     # accepted, not yet en route
    (210.0, "on_the_way"),   # operator en route
    (150.0, "completed"),    # fully closed out
]


async def _get_or_create_user(db, *, email: str, full_name: str, role: UserRole) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is not None:
        print(f"User '{email}' already exists — skipping.")
        return user
    user = User(
        email=email,
        full_name=full_name,
        role=role,
        hashed_password=hash_password(PASSWORD),
    )
    db.add(user)
    await db.flush()
    print(f"Created user '{email}' ({role.value}).")
    return user


async def _advance(service: RequestService, req: CollectionRequest, stage: str, operator: User) -> None:
    """Drive a freshly-created (PENDING) request forward to the target stage."""
    if stage == "pending":
        return
    if stage == "rejected":
        await service.decide(
            req.id,
            RequestDecision(accept=False, rejection_reason="Too contaminated for methanization"),
            operator,
        )
        return

    # All remaining stages start by accepting.
    await service.decide(req.id, RequestDecision(accept=True), operator)
    if stage == "accepted":
        return

    await service.transition(req.id, RequestTransition(target=RequestStatus.ON_THE_WAY), operator)
    if stage == "on_the_way":
        return

    await service.transition(
        req.id,
        RequestTransition(target=RequestStatus.COLLECTED, collected_weight_kg=req.declared_weight_kg),
        operator,
    )
    if stage == "collected":
        return

    await service.transition(req.id, RequestTransition(target=RequestStatus.COMPLETED), operator)


async def seed_demo_requests() -> None:
    async with AsyncSessionLocal() as db:
        manager = await _get_or_create_user(
            db, email=MANAGER_EMAIL, full_name="Demo Manager", role=UserRole.HOTEL_MANAGER
        )
        operator = await _get_or_create_user(
            db, email=OPERATOR_EMAIL, full_name="Demo Operator", role=UserRole.OPERATOR
        )

        hotel = await db.scalar(select(Hotel).where(Hotel.name == HOTEL_NAME))
        if hotel is None:
            hotel = Hotel(
                name=HOTEL_NAME,
                city="Djerba",
                status=HotelStatus.ACTIVE,
                latitude=33.8076,
                longitude=10.9975,
                manager_id=manager.id,
            )
            db.add(hotel)
            await db.flush()
            print(f"Created hotel '{HOTEL_NAME}' managed by {MANAGER_EMAIL}.")
        elif hotel.manager_id != manager.id:
            hotel.manager_id = manager.id
            await db.flush()
            print(f"Reassigned hotel '{HOTEL_NAME}' to {MANAGER_EMAIL}.")
        else:
            print(f"Hotel '{HOTEL_NAME}' already exists — skipping create.")

        await db.commit()

        # Only seed requests if the demo hotel has none, so re-runs don't pile up.
        existing = await RequestRepository(db).count(
            filters=[CollectionRequest.hotel_id == hotel.id]
        )
        if existing:
            print(f"Hotel already has {existing} request(s) — skipping request seed.")
            return

        service = RequestService(db)
        for declared_kg, stage in DEMO_REQUESTS:
            req = await service.create(
                CollectionRequestCreate(declared_weight_kg=declared_kg),
                manager,
                hotel_id=hotel.id,
            )
            await _advance(service, req, stage, operator)
            print(f"  Created request {declared_kg} kg -> {stage} (priority {req.ai_priority_score}).")

        print(f"\nDone. Seeded {len(DEMO_REQUESTS)} requests for '{HOTEL_NAME}'.")
        print(f"Log in as {MANAGER_EMAIL} / {PASSWORD} (hotel) or {OPERATOR_EMAIL} / {PASSWORD} (queue).")


if __name__ == "__main__":
    asyncio.run(seed_demo_requests())
