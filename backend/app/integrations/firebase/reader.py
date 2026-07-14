"""FirebaseRealtimeReader — reads camera detections and produces request analysis.

Implements the `RequestDataProvider` interface, so the business layer swaps stub
→ Firebase with a one-line change and no domain code change. STRICTLY READ-ONLY:
this class exposes no write path and never mutates Firebase.

Auth: if a service-account key is configured, we mint a short-lived OAuth2 token
and read authenticated; otherwise we read unauthenticated (works only while the
DB rules are public — intended as a transition state, not for production).
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.features.requests.schemas import AIResult
from app.integrations.firebase.aggregator import aggregate_detections, summarize_live

logger = get_logger(__name__)

# Scopes needed to read the Realtime Database via REST with a service account.
_RTDB_SCOPES = [
    "https://www.googleapis.com/auth/firebase.database",
    "https://www.googleapis.com/auth/userinfo.email",
]


class FirebaseError(Exception):
    """Raised when Firebase can't be read; callers decide the fallback."""


class FirebaseRealtimeReader:
    """Read-only RequestDataProvider backed by Firebase Realtime Database."""

    def __init__(
        self,
        *,
        db_url: str | None = None,
        credentials_path: str | None = None,
        node: str | None = None,
    ) -> None:
        self._db_url = (db_url or settings.FIREBASE_DB_URL).rstrip("/")
        self._credentials_path = credentials_path or settings.FIREBASE_CREDENTIALS_PATH
        self._node = node or settings.FIREBASE_DETECTIONS_NODE
        self._credentials = None  # lazily loaded google.auth credentials

    # ------------------------------------------------------------------ auth
    def _access_token(self) -> str | None:
        """Mint (and cache) an OAuth token from the service-account key.

        Returns None when no key is configured (unauthenticated read path).
        """
        if not self._credentials_path:
            return None
        # Import here so the dependency is only needed when a key is used.
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import service_account

        if self._credentials is None:
            self._credentials = service_account.Credentials.from_service_account_file(
                self._credentials_path, scopes=_RTDB_SCOPES
            )
        if not self._credentials.valid:
            self._credentials.refresh(GoogleRequest())
        return self._credentials.token

    # ------------------------------------------------------------------ read
    async def _fetch_node(self) -> dict[str, Any]:
        """GET the detections node as JSON. Read-only."""
        if not self._db_url:
            raise FirebaseError("FIREBASE_DB_URL is not configured")

        url = f"{self._db_url}/{self._node}.json"
        params: dict[str, str] = {}
        token = self._access_token()
        if token:
            params["access_token"] = token

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise FirebaseError(
                f"Firebase read failed: HTTP {resp.status_code} {resp.text[:200]}"
            )
        data = resp.json()
        return data if isinstance(data, dict) else {}

    # -------------------------------------------------- RequestDataProvider
    async def get_analysis(
        self, *, request_id: uuid.UUID, declared_weight_kg: float
    ) -> AIResult:
        """Read the latest detections and aggregate them into an AIResult.

        Strategy: latest-snapshot — the detections present in the node right now
        represent the current intake being scanned. (One camera = one hotel for
        the current single-site setup.)
        """
        node = await self._fetch_node()
        detections = node.get("detections", {})
        if not isinstance(detections, dict):
            detections = {}
        return aggregate_detections(detections, declared_weight_kg=declared_weight_kg)

    async def get_live_summary(self) -> dict[str, Any]:
        """Current camera state for the live dashboard panel (read-only)."""
        node = await self._fetch_node()
        return summarize_live(node)
