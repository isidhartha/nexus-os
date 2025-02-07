"""Smart home / IoT integration via MQTT (Home Assistant compatible)."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger
from ..shared.models import IoTDevice

logger = get_logger(__name__)


class SmartHomeManager:
    """MQTT client for IoT device control and state tracking."""

    def __init__(self) -> None:
        settings = get_settings()
        self.broker = settings.mqtt_broker
        self.port = settings.mqtt_port
        self._client = None
        self._devices: Dict[str, IoTDevice] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._connected = False
        self._available = False
        self._init_mqtt()

    def _init_mqtt(self) -> None:
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import]

            self._client = mqtt.Client(client_id="nexus-os", clean_session=True)
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            self._available = True
            logger.info("MQTT client initialized (broker=%s:%d)", self.broker, self.port)
        except ImportError:
            logger.warning("paho-mqtt not installed — SmartHome in mock mode")

    def connect(self, timeout: float = 5.0) -> bool:
        if not self._available or not self._client:
            return False
        try:
            self._client.connect_async(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            logger.info("MQTT connecting to %s:%d", self.broker, self.port)
            return True
        except Exception as exc:
            logger.error("MQTT connect error: %s", exc)
            return False

    def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self._connected = True
            logger.info("MQTT connected")
            client.subscribe("homeassistant/#")
            client.subscribe("nexus/+/state")
        else:
            logger.error("MQTT connection failed rc=%d", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._connected = False
        logger.warning("MQTT disconnected rc=%d", rc)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            topic = msg.topic
            payload_str = msg.payload.decode("utf-8")
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                payload = {"value": payload_str}

            self._handle_device_state(topic, payload)

            for pattern, callbacks in self._callbacks.items():
                if self._topic_matches(pattern, topic):
                    for cb in callbacks:
                        cb(topic, payload)
        except Exception as exc:
            logger.error("MQTT message processing error: %s", exc)

    def _handle_device_state(self, topic: str, payload: Dict[str, Any]) -> None:
        parts = topic.split("/")
        if len(parts) >= 2:
            device_id = parts[1]
            if device_id not in self._devices:
                self._devices[device_id] = IoTDevice(
                    id=device_id,
                    name=device_id,
                    type="unknown",
                )
            device = self._devices[device_id]
            device.state.update(payload)
            device.online = True
            device.last_seen = datetime.utcnow()

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")
        if len(pattern_parts) != len(topic_parts):
            return "#" not in pattern
        return all(
            pp == tp or pp == "+" or pp == "#"
            for pp, tp in zip(pattern_parts, topic_parts)
        )

    def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False) -> bool:
        if not self._connected or not self._client:
            logger.debug("[MOCK MQTT] publish %s: %s", topic, payload)
            return True
        payload_str = json.dumps(payload) if isinstance(payload, dict) else str(payload)
        result = self._client.publish(topic, payload_str, qos=qos, retain=retain)
        return result.rc == 0

    def control_device(self, device_id: str, command: str, value: Any = None) -> bool:
        topic = f"nexus/{device_id}/command"
        payload = {"command": command, "value": value}
        return self.publish(topic, payload)

    def subscribe_topic(self, topic: str, callback: Callable) -> None:
        if topic not in self._callbacks:
            self._callbacks[topic] = []
        self._callbacks[topic].append(callback)
        if self._client and self._connected:
            self._client.subscribe(topic)

    def register_device(self, device: IoTDevice) -> None:
        self._devices[device.id] = device
        logger.info("Registered device: %s (%s)", device.name, device.id)

    def list_devices(self) -> List[IoTDevice]:
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        return self._devices.get(device_id)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_available(self) -> bool:
        return self._available
