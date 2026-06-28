"""Single import surface for Alembic autogenerate.

Alembic can only detect tables whose model classes have been imported. Rather
than scattering imports through `env.py`, every feature registers its models
here as it is built. Import this module to populate `Base.metadata`.
"""

from app.shared.models import Base

# As features are added, import their models so Alembic sees them, e.g.:
# from app.features.auth.models import User  # noqa: F401
# from app.features.hotels.models import Hotel  # noqa: F401

__all__ = ["Base"]
