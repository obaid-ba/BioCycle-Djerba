"""MQTT consumer lifecycle.

paho runs its network loop on a background thread; incoming messages are
bridged back onto the application's asyncio loop via `run_coroutine_threadsafe`
so all DB/broadcast work happens on the main event loop.
"""

import asyncio

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.logging import get_logger
from app.mqtt.processor import process_message

logger = get_logger(__name__)

# Module-level connection state so request handlers (e.g. dashboard status) can
# report broker health without holding a reference to the consumer instance.
_connected = False


def is_mqtt_connected() -> bool:
    return _connected


class MQTTConsumer:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._client = mqtt.Client(
            client_id="biocycle-backend",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if settings.MQTT_USERNAME:
            self._client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD or None)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self) -> None:
        try:
            self._client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
        except OSError as exc:
            logger.warning(
                "MQTT broker unreachable at %s:%s (%s). Consumer is idle; "
                "the API remains fully functional.",
                settings.MQTT_HOST,
                settings.MQTT_PORT,
                exc,
            )
            return
        self._client.loop_start()
        logger.info("MQTT consumer started")

    def stop(self) -> None:
        self._client.loop_stop()
        try:
            self._client.disconnect()
        except Exception:  # pragma: no cover - best-effort shutdown
            pass

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        global _connected
        _connected = True
        client.subscribe(settings.MQTT_TOPIC)
        logger.info("MQTT subscribed to %s", settings.MQTT_TOPIC)

    def _on_disconnect(self, client, userdata, *args) -> None:
        global _connected
        _connected = False
        logger.warning("MQTT disconnected")

    def _on_message(self, client, userdata, message) -> None:
        # Runs on paho's network thread — hand off to the asyncio loop.
        asyncio.run_coroutine_threadsafe(
            process_message(message.topic, message.payload), self._loop
        )
