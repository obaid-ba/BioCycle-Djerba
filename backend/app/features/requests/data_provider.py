"""Request-analysis data provider — the abstraction that hides the data source.

The backend never computes AI scores. Analysis data (weight + AI outputs) comes
from an external source: today a local stub, later Firebase (fed by the hotel's
Raspberry Pi). The business layer depends only on the `RequestDataProvider`
interface (Adapter pattern + dependency injection), so it never knows — or
cares — whether the data is stubbed or live.

Target hierarchy (only the stub exists today):

    RequestDataProvider          (interface / Protocol)
        ├── StubRequestDataProvider      (deterministic, for dev/test/demo)
        └── FirebaseRealtimeReader       (future — reads Firebase, read-only)

Swapping the implementation is a one-line change in the DI wiring; no business
code changes.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Protocol

from app.features.requests.schemas import AIResult

STUB_PROVIDER_VERSION = "stub-provider-0.1.0"


class RequestDataProvider(Protocol):
    """Contract for a source of a request's analysis data.

    Given the request's identity and declared weight, return the normalized
    `AIResult` (quality/purity/methane/priority/…). Implementations decide where
    the data comes from — a deterministic stub, or Firebase. Any extra inputs the
    real source needs (photos, device id) are implementation details hidden here.
    """

    async def get_analysis(
        self, *, request_id: uuid.UUID, declared_weight_kg: float
    ) -> AIResult:
        ...


def _unit_hash(request_id: uuid.UUID, salt: str) -> float:
    """Deterministic float in [0, 1) from the request id + a salt.

    Using the id (not randomness) makes results reproducible: the same request
    always yields the same analysis, keeping tests and demos stable.
    """
    digest = hashlib.sha256(f"{request_id}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


class StubRequestDataProvider:
    """Deterministic placeholder provider. Implements `RequestDataProvider`.

    Stands in for Firebase/Raspberry until the integration lands, producing
    stable, plausible analysis so the operator queue has a real ordering.
    """

    async def get_analysis(
        self, *, request_id: uuid.UUID, declared_weight_kg: float
    ) -> AIResult:
        # Purity drives quality/contamination; larger loads get a mild priority
        # bump so the queue favors high-yield pickups, but purity dominates.
        organic_purity = round(60 + _unit_hash(request_id, "purity") * 39, 1)  # 60..99 %
        contamination = round(100 - organic_purity, 1)
        quality_score = round(organic_purity * 0.9 + _unit_hash(request_id, "q") * 10, 1)

        # Rough, transparent yield model (placeholder coefficients):
        #   biogas ≈ organic mass × purity × yield factor.
        organic_mass = declared_weight_kg * (organic_purity / 100)
        methane_m3 = round(organic_mass * 0.18, 2)
        energy_kwh = round(methane_m3 * 10.0, 2)      # ~10 kWh per m³ methane
        co2_kg = round(methane_m3 * 1.9, 2)           # avoided CO₂ proxy

        # Priority blends quality with load size, normalized to 0..100.
        weight_factor = min(declared_weight_kg / 500.0, 1.0)  # saturates at 500 kg
        priority = round(quality_score * 0.7 + weight_factor * 30, 1)

        confidence = round(0.75 + _unit_hash(request_id, "conf") * 0.24, 2)  # 0.75..0.99

        return AIResult(
            quality_score=quality_score,
            organic_purity=organic_purity,
            contamination=contamination,
            estimated_methane_m3=methane_m3,
            estimated_energy_kwh=energy_kwh,
            estimated_co2_kg=co2_kg,
            priority_score=priority,
            confidence=confidence,
            model_version=STUB_PROVIDER_VERSION,
        )


#: The default provider used until Firebase is wired. Swap this (or override via
#: DI) to change the data source — the business layer is untouched.
default_provider: RequestDataProvider = StubRequestDataProvider()
