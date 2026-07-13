"""Report DTOs."""

from datetime import datetime

from app.shared.schemas import BaseSchema


class ReportPeriod(BaseSchema):
    date_from: datetime
    date_to: datetime


class ReportTotals(BaseSchema):
    requests: int
    declared_weight_kg: float
    collected_weight_kg: float
    estimated_methane_m3: float
    estimated_energy_kwh: float
    estimated_co2_kg: float


class ReportTopHotel(BaseSchema):
    hotel_name: str
    request_count: int
    total_methane_m3: float


class ReportSummary(BaseSchema):
    period: ReportPeriod
    totals: ReportTotals
    status_counts: dict[str, int]
    avg_quality_score: float | None
    acceptance_rate: float | None
    top_hotels: list[ReportTopHotel]
