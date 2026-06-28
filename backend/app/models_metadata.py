"""Single import surface for Alembic autogenerate.

Alembic can only detect tables whose model classes have been imported. Rather
than scattering imports through `env.py`, every feature registers its models
here as it is built. Import this module to populate `Base.metadata`.
"""

from app.features.auth.models import User  # noqa: F401
from app.features.bins.models import SensorReading, SmartBin  # noqa: F401
from app.features.hotels.models import Hotel  # noqa: F401
from app.shared.models import Base

__all__ = ["Base"]
