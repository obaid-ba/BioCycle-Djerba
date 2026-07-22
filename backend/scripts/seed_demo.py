"""Idempotently seed demo data for exercising the app end-to-end.

Creates an operator, hotel managers, real Djerba hotels (with coordinates, so
the operator's request map has something to draw), and collection requests
spread across the lifecycle.

Run after migrations and seed_admin:  python -m scripts.seed_demo

Idempotent: keyed on user email and hotel name, so re-running adds nothing.
Requests are only created for hotels that have none yet, keeping the script
safe to re-run without inflating the queue.

Everything goes through the real service layer, so seeded requests get the same
AI scores, distance-to-plant snapshot, and guarded transitions as production
traffic — the demo data is indistinguishable from real data.
"""

import asyncio
import uuid

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.features.auth.models import User, UserRole
from app.features.auth.repository import UserRepository
from app.features.hotels.models import Hotel, HotelStatus
from app.features.hotels.repository import HotelRepository
from app.features.requests.schemas import (
    CollectionRequestCreate,
    RequestDecision,
    RequestTransition,
)
from app.features.requests.service import RequestService
from app.features.requests.state_machine import RequestStatus
from app.shared.schemas import PaginationParams

DEMO_PASSWORD = "Demo1234!"

# Real hotel zones around Djerba. Coordinates are genuine, so distances to the
# plant (33.68, 10.91 — see settings.PLANT_LATITUDE/LONGITUDE) are meaningful
# and the queue's proximity tiebreak is visibly exercised.
HOTELS: list[dict] = [
    {
        "name": "Radisson Blu Palace Resort",
        "address": "Zone Touristique Sidi Mahrez",
        "city": "Midoun",
        "latitude": 33.8869,
        "longitude": 10.9639,
        "manager_email": "manager.radisson@biocycle.tn",
        "manager_name": "Sonia Trabelsi",
    },
    {
        "name": "Djerba Plaza Thalasso",
        "address": "Route Touristique Sidi Mahrez",
        "city": "Midoun",
        "latitude": 33.8752,
        "longitude": 10.9525,
        "manager_email": "manager.plaza@biocycle.tn",
        "manager_name": "Karim Bouazizi",
    },
    {
        "name": "Hotel El Mouradi Djerba Menzel",
        "address": "Zone Touristique Aghir",
        "city": "Midoun",
        "latitude": 33.7644,
        "longitude": 11.0164,
        "manager_email": "manager.mouradi@biocycle.tn",
        "manager_name": "Amel Gharbi",
    },
    {
        "name": "Seabel Rym Beach",
        "address": "Zone Touristique Sidi Mahrez",
        "city": "Houmt Souk",
        "latitude": 33.8944,
        "longitude": 10.8583,
        "manager_email": "manager.seabel@biocycle.tn",
        "manager_name": "Nizar Ben Salah",
    },
    {
        "name": "Dar Ali Guesthouse",
        "address": "Rue Mohamed Badra, Houmt Souk",
        "city": "Houmt Souk",
        "latitude": 33.8756,
        "longitude": 10.8578,
        "manager_email": "manager.darali@biocycle.tn",
        "manager_name": "Leila Mansour",
    },
]

# Requests to create per hotel, by hotel name: (containers, final lifecycle state).
# Chosen to leave the operator queue with a mix of work: things awaiting a
# decision, things in flight, and finished history.
REQUEST_PLAN: dict[str, list[tuple[int, RequestStatus]]] = {
    "Radisson Blu Palace Resort": [
        (4, RequestStatus.PENDING),
        (2, RequestStatus.COMPLETED),
        (3, RequestStatus.ON_THE_WAY),
    ],
    "Djerba Plaza Thalasso": [
        (5, RequestStatus.PENDING),
        (1, RequestStatus.REJECTED),
    ],
    "Hotel El Mouradi Djerba Menzel": [
        (3, RequestStatus.ACCEPTED),
        (6, RequestStatus.COLLECTED),
    ],
    "Seabel Rym Beach": [
        (2, RequestStatus.PENDING),
        (4, RequestStatus.COMPLETED),
    ],
    "Dar Ali Guesthouse": [
        (1, RequestStatus.PENDING),
    ],
}


async def _get_or_create_user(
    repo: UserRepository, *, email: str, full_name: str, role: UserRole
) -> User:
    existing = await repo.get_by_email(email)
    if existing is not None:
        return existing
    user = await repo.add(
        User(
            email=email,
            full_name=full_name,
            role=role,
            hashed_password=hash_password(DEMO_PASSWORD),
        )
    )
    print(f"  + user {email} ({role.value})")
    return user


async def _get_hotel_by_name(repo: HotelRepository, name: str) -> Hotel | None:
    hotels, _ = await repo.search(
        params=PaginationParams(page=1, page_size=100), search=name
    )
    return next((h for h in hotels if h.name == name), None)


async def _drive_to(
    service: RequestService,
    request_id: uuid.UUID,
    operator: User,
    target: RequestStatus,
) -> None:
    """Walk a freshly created (PENDING) request to `target` via the real service.

    Each hop is a genuine, guarded transition — the same path the operator UI
    takes — so seeded rows carry correct decided_by/decided_at/completed_at.
    """
    if target == RequestStatus.PENDING:
        return

    if target == RequestStatus.REJECTED:
        await service.decide(
            request_id,
            RequestDecision(
                accept=False,
                rejection_reason="Contamination above the accepted threshold.",
            ),
            operator,
        )
        return

    # Everything else starts by accepting.
    await service.decide(
        request_id, RequestDecision(accept=True, notes="Seeded demo request."), operator
    )
    if target == RequestStatus.ACCEPTED:
        return

    await service.transition(
        request_id, RequestTransition(target=RequestStatus.ON_THE_WAY), operator
    )
    if target == RequestStatus.ON_THE_WAY:
        return

    # The truck weighs the real load; make it differ slightly from the declared
    # amount, as it would in the field.
    req = await service.requests.get(request_id)
    assert req is not None
    await service.transition(
        request_id,
        RequestTransition(
            target=RequestStatus.COLLECTED,
            collected_weight_kg=round(req.declared_weight_kg * 0.93, 2),
        ),
        operator,
    )
    if target == RequestStatus.COLLECTED:
        return

    await service.transition(
        request_id, RequestTransition(target=RequestStatus.COMPLETED), operator
    )


async def seed_demo() -> None:
    async with AsyncSessionLocal() as db:
        users = UserRepository(db)
        hotels_repo = HotelRepository(db)
        service = RequestService(db)

        print("Seeding users…")
        operator = await _get_or_create_user(
            users,
            email="operator@biocycle.tn",
            full_name="Mehdi Jelassi",
            role=UserRole.OPERATOR,
        )

        print("Seeding hotels…")
        created_hotels: list[Hotel] = []
        for spec in HOTELS:
            manager = await _get_or_create_user(
                users,
                email=spec["manager_email"],
                full_name=spec["manager_name"],
                role=UserRole.HOTEL_MANAGER,
            )
            await db.flush()

            hotel = await _get_hotel_by_name(hotels_repo, spec["name"])
            if hotel is None:
                hotel = await hotels_repo.add(
                    Hotel(
                        name=spec["name"],
                        address=spec["address"],
                        city=spec["city"],
                        country="Tunisia",
                        latitude=spec["latitude"],
                        longitude=spec["longitude"],
                        contact_email=spec["manager_email"],
                        status=HotelStatus.ACTIVE,
                        manager_id=manager.id,
                    )
                )
                print(f"  + hotel {spec['name']} ({spec['city']})")
            created_hotels.append(hotel)

        await db.commit()

        print("Seeding collection requests…")
        for hotel in created_hotels:
            manager = await users.get(hotel.manager_id) if hotel.manager_id else None
            if manager is None:
                continue

            # Skip hotels that already have requests so re-runs don't pile up.
            existing, total = await service.requests.search(
                params=PaginationParams(page=1, page_size=1), hotel_id=hotel.id
            )
            if total > 0:
                print(f"  = {hotel.name}: {total} request(s) already — skipping")
                continue

            for containers, target in REQUEST_PLAN.get(hotel.name, []):
                req = await service.create(
                    CollectionRequestCreate(declared_containers=containers),
                    manager,
                    hotel_id=hotel.id,
                )
                await _drive_to(service, req.id, operator, target)
                print(
                    f"  + {hotel.name}: {containers} cont. -> {target.value} "
                    f"({req.distance_to_plant_km} km to plant)"
                )

    print(
        "\nDone. Demo logins (password "
        f"'{DEMO_PASSWORD}'):\n"
        "  operator@biocycle.tn            (operator — sees the queue + map)\n"
        + "".join(f"  {h['manager_email']:<32}(hotel)\n" for h in HOTELS)
    )


if __name__ == "__main__":
    asyncio.run(seed_demo())
