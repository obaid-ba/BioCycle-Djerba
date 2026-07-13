"""Local, deterministic AI scorer — the seam where the external AI team plugs in.

The real analysis is built by another team and reached over HTTP. Until it lands
(and for tests/demos), `StubAIScorer` produces stable, plausible scores so the
operator queue has a real priority ordering. Both implement `AIScorer`, so the
service depends only on the protocol (dependency inversion) and swapping in the
HTTP client later touches no business code.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Protocol

from app.features.requests.schemas import AIResult

STUB_MODEL_VERSION = "stub-ai-0.1.0"


class AIScorer(Protocol):
    """Contract for anything that scores a collection request.

    Kept intentionally minimal: given the request's identity and declared
    weight, return normalized `AIResult` scores. The real client will also send
    photos; that extra input is an implementation detail behind this seam.
    """

    async def score(self, *, request_id: uuid.UUID, declared_weight_kg: float) -> AIResult:
        ...


def _unit_hash(request_id: uuid.UUID, salt: str) -> float:
    """Deterministic float in [0, 1) derived from the request id and a salt.

    Using the id (not randomness) makes every score reproducible: the same
    request always yields the same analysis, which keeps tests and demos stable.
    """
    digest = hashlib.sha256(f"{request_id}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


class StubAIScorer:
    """Deterministic placeholder scorer. Implements `AIScorer`."""

    async def score(
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
            model_version=STUB_MODEL_VERSION,
        )


#: Default scorer used by the service until the real HTTP client is wired.
default_scorer: AIScorer = StubAIScorer()
