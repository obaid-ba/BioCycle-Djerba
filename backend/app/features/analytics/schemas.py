"""Analytics & dashboard DTOs (read-only aggregates)."""

from app.shared.schemas import BaseSchema


class SystemStatus(BaseSchema):
    ai: str
    mqtt: str
    websocket: str
    websocket_connections: int


class DashboardStats(BaseSchema):
    today_collections: int
    organic_waste_kg: float
    non_organic_waste_kg: float
    total_waste_kg: float
    predicted_energy_kwh: float
    predicted_biogas_m3: float
    co2_saved_kg: float
    hotels_connected: int
    total_bins: int
    online_bins: int
    open_alerts: int
    system: SystemStatus


class WasteDistribution(BaseSchema):
    organic_kg: float
    non_organic_kg: float
    total_kg: float
    organic_percentage: float | None


class TimeseriesBucket(BaseSchema):
    bucket: str
    count: int
    organic_kg: float
    non_organic_kg: float
    total_kg: float


# --------------------------------------------------------------------------- #
# Request-centric analytics (the current product's source of truth)
# --------------------------------------------------------------------------- #
class RequestStats(BaseSchema):
    """Headline KPIs derived from collection_requests."""

    total_requests: int
    status_counts: dict[str, int]  # keyed by RequestStatus value
    declared_weight_kg: float
    collected_weight_kg: float
    estimated_methane_m3: float
    estimated_energy_kwh: float
    estimated_co2_kg: float
    avg_quality_score: float | None
    acceptance_rate: float | None  # decided-and-not-rejected / decided


class HotelRankingRow(BaseSchema):
    hotel_id: str
    hotel_name: str
    request_count: int
    total_weight_kg: float
    total_methane_m3: float
    avg_quality_score: float | None


class OperatorRankingRow(BaseSchema):
    operator_id: str
    operator_name: str
    handled_count: int
    completed_count: int


class RequestTimeseriesBucket(BaseSchema):
    bucket: str
    count: int
    declared_weight_kg: float
    estimated_methane_m3: float
