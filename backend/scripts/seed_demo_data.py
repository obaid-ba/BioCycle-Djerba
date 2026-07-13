"""Idempotently seed demo hotels and smart bins for local development.

Run after migrations:  python -m scripts.seed_demo_data

Creates a handful of real Djerba hotels (with approximate coordinates) and a few
smart bins per hotel. Safe to re-run: hotels are matched by name and bins by code,
so existing rows are left untouched.
"""

import asyncio
from datetime import datetime, timezone

import app.models_metadata  # noqa: F401  — registers all models so FKs resolve
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.features.bins.models import BinStatus, BinType, SmartBin
from app.features.hotels.models import Hotel, HotelStatus

# (name, address, city, lat, lon, rooms, status)
HOTELS = [
    ("Radisson Blu Palace Resort", "Zone Touristique, Midoun", "Djerba",
     33.8456, 10.9860, 294, HotelStatus.ACTIVE),
    ("Djerba Plaza Thalasso & Spa", "Zone Touristique Sidi Mahrez", "Djerba",
     33.8712, 10.8570, 320, HotelStatus.ACTIVE),
    ("Hotel Palm Beach Palace", "Zone Touristique Aghir", "Djerba",
     33.7920, 11.0210, 210, HotelStatus.ACTIVE),
    ("Iberostar Mehari Djerba", "Zone Touristique Sidi Mahrez", "Djerba",
     33.8640, 10.8680, 262, HotelStatus.ONBOARDING),
    ("Seabel Aladin Djerba", "Zone Touristique Aghir", "Djerba",
     33.8030, 11.0050, 180, HotelStatus.INACTIVE),
]

# Per hotel: (code_suffix, name, type, status, capacity, fill, battery)
BINS_PER_HOTEL = [
    ("ORG-01", "Kitchen — Organic", BinType.ORGANIC, BinStatus.ONLINE, 240.0, 62.0, 88.0),
    ("ORG-02", "Restaurant — Organic", BinType.ORGANIC, BinStatus.ONLINE, 240.0, 91.0, 74.0),
    ("MIX-01", "Lobby — Mixed", BinType.MIXED, BinStatus.ONLINE, 120.0, 35.0, 95.0),
    ("NON-01", "Pool Bar — Non-organic", BinType.NON_ORGANIC, BinStatus.OFFLINE, 120.0, None, None),
]


async def seed_demo_data() -> None:
    now = datetime.now(timezone.utc)
    created_hotels = 0
    created_bins = 0

    async with AsyncSessionLocal() as db:
        for name, address, city, lat, lon, rooms, status in HOTELS:
            existing = await db.scalar(
                select(Hotel).where(Hotel.name == name).limit(1)
            )
            if existing is not None:
                print(f"Hotel '{name}' already exists — skipping.")
                hotel_id = existing.id
            else:
                hotel = Hotel(
                    name=name,
                    address=address,
                    city=city,
                    country="Tunisia",
                    latitude=lat,
                    longitude=lon,
                    number_of_rooms=rooms,
                    status=status,
                )
                db.add(hotel)
                await db.flush()  # assign hotel.id
                hotel_id = hotel.id
                created_hotels += 1
                print(f"Created hotel '{name}'.")

            # Derive a short code prefix from the hotel name initials.
            prefix = "".join(w[0] for w in name.split()[:3]).upper()
            for suffix, bin_name, bin_type, bin_status, capacity, fill, battery in BINS_PER_HOTEL:
                code = f"{prefix}-{suffix}"
                exists = await db.scalar(
                    select(SmartBin).where(SmartBin.code == code).limit(1)
                )
                if exists is not None:
                    print(f"  Bin '{code}' already exists — skipping.")
                    continue
                db.add(
                    SmartBin(
                        code=code,
                        name=bin_name,
                        hotel_id=hotel_id,
                        bin_type=bin_type,
                        status=bin_status,
                        capacity_liters=capacity,
                        latitude=lat,
                        longitude=lon,
                        fill_level=fill,
                        battery_level=battery,
                        last_reading_at=now if bin_status == BinStatus.ONLINE else None,
                    )
                )
                created_bins += 1
                print(f"  Created bin '{code}' ({bin_name}).")

        await db.commit()

    print(f"\nDone. Created {created_hotels} hotel(s) and {created_bins} bin(s).")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
