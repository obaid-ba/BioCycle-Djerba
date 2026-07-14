"""Aggregate raw camera detections into normalized request analysis.

The vision model classifies each item it sees as organic ("O") or recyclable /
non-organic ("R") with a confidence in [0, 1]. This module turns a batch of such
detections + the hotel's declared weight into an `AIResult` (purity, quality,
methane, priority, …). Pure functions — no Firebase, no I/O — so it's trivially
testable and reused by both the live reader and its stub.
"""

from __future__ import annotations

from typing import Any

from app.features.requests.schemas import AIResult

FIREBASE_MODEL_VERSION = "firebase-vision-0.1.0"

# Labels the vision model emits.
LABEL_ORGANIC = "O"
LABEL_RECYCLABLE = "R"


def _extract_counts(detections: dict[str, Any]) -> tuple[int, int, float]:
    """From a Firebase `detections` map, return (organic, recyclable, avg_conf).

    Ignores malformed entries defensively — a stray record must not break a
    hotel's request creation.
    """
    organic = 0
    recyclable = 0
    confidences: list[float] = []
    for entry in (detections or {}).values():
        if not isinstance(entry, dict):
            continue
        label = entry.get("prediction")
        conf = entry.get("confidence")
        if label == LABEL_ORGANIC:
            organic += 1
        elif label == LABEL_RECYCLABLE:
            recyclable += 1
        else:
            continue  # unknown label — don't count it either way
        if isinstance(conf, (int, float)):
            confidences.append(float(conf))
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return organic, recyclable, avg_conf


def summarize_live(node: dict[str, Any]) -> dict[str, Any]:
    """Turn a raw /AI_System node into a live camera summary for the dashboard.

    Unlike `aggregate_detections` (which produces request analysis), this is the
    real-time view: what the camera is seeing right now, plus its status.
    """
    detections = node.get("detections") if isinstance(node, dict) else None
    if not isinstance(detections, dict):
        detections = {}
    organic, recyclable, avg_conf = _extract_counts(detections)
    total = organic + recyclable
    purity = round(organic / total * 100, 1) if total else None

    return {
        "camera": node.get("camera") if isinstance(node, dict) else None,
        "fps": node.get("fps") if isinstance(node, dict) else None,
        "resolution": node.get("resolution") if isinstance(node, dict) else None,
        "objects_detected": node.get("objects_detected") if isinstance(node, dict) else None,
        "last_update": node.get("time") if isinstance(node, dict) else None,
        "organic_count": organic,
        "recyclable_count": recyclable,
        "total_detections": total,
        "organic_purity": purity,
        "avg_confidence": round(avg_conf, 2) if total else None,
    }


def aggregate_detections(
    detections: dict[str, Any], *, declared_weight_kg: float
) -> AIResult:
    """Turn a batch of O/R detections + declared weight into an `AIResult`.

    Composition (from detections):
      organic_purity = O / (O + R) × 100
      contamination  = 100 − purity
      quality_score  = purity weighted by average detection confidence
      confidence     = average detection confidence

    Yield (from purity × declared mass; same transparent coefficients as the
    stub so numbers stay comparable):
      methane ≈ organic_mass × 0.18,  energy ≈ methane × 10,  co2 ≈ methane × 1.9

    Priority blends quality with load size, normalized to 0..100.
    """
    organic, recyclable, avg_conf = _extract_counts(detections)
    total = organic + recyclable

    if total == 0:
        # No usable detections: report a neutral, low-confidence result rather
        # than failing. The request is still created; the operator sees the gap.
        organic_purity = 0.0
        contamination = 0.0
        quality_score = 0.0
        confidence = 0.0
    else:
        organic_purity = round(organic / total * 100, 1)
        contamination = round(100 - organic_purity, 1)
        # Quality = purity scaled by how confident the model was.
        quality_score = round(organic_purity * (0.5 + 0.5 * avg_conf), 1)
        confidence = round(avg_conf, 2)

    organic_mass = declared_weight_kg * (organic_purity / 100)
    methane_m3 = round(organic_mass * 0.18, 2)
    energy_kwh = round(methane_m3 * 10.0, 2)
    co2_kg = round(methane_m3 * 1.9, 2)

    weight_factor = min(declared_weight_kg / 5000.0, 1.0)  # saturates at ~7 containers
    priority = round(quality_score * 0.7 + weight_factor * 30, 1)

    return AIResult(
        quality_score=quality_score,
        organic_purity=organic_purity,
        contamination=contamination,
        estimated_methane_m3=methane_m3,
        estimated_energy_kwh=energy_kwh,
        estimated_co2_kg=co2_kg,
        priority_score=priority,
        confidence=confidence,
        model_version=FIREBASE_MODEL_VERSION,
    )
