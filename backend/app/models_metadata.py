"""Single import surface for Alembic autogenerate.

Alembic can only detect tables whose model classes have been imported. Rather
than scattering imports through `env.py`, every feature registers its models
here as it is built. Import this module to populate `Base.metadata`.
"""

from app.features.activity.models import ActivityLog  # noqa: F401
from app.features.alerts.models import Alert  # noqa: F401
from app.features.auth.models import User  # noqa: F401
from app.features.bins.models import SensorReading, SmartBin  # noqa: F401
from app.features.collections.models import (  # noqa: F401
    Prediction,
    WasteCollection,
)
from app.features.hotels.models import Hotel  # noqa: F401
from app.features.notifications.models import Notification  # noqa: F401
from app.features.requests.models import (  # noqa: F401
    CollectionRequest,
    RequestPhoto,
)
from app.shared.models import Base

__all__ = ["Base"]
