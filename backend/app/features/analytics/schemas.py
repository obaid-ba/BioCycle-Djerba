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
