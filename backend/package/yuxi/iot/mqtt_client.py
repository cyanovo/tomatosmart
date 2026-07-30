from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Callable, Awaitable, TYPE_CHECKING

from yuxi.iot.schemas import AirSensorData, SoilSensorData, IrrigationCommand
from yuxi.utils import logger

if TYPE_CHECKING:
    import paho.mqtt.client as mqtt

# ---- 默认配置 ----
BROKER_URL = os.environ.get("MQTT_BROKER_URL", "broker.emqx.io")
BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
BROKER_USERNAME = os.environ.get("MQTT_BROKER_USERNAME", "admin")
BROKER_PASSWORD = os.environ.get("MQTT_BROKER_PASSWORD", "admin123")
CLIENT_ID = f"yuxi-server-{int(time.time())}"
KEEPALIVE = 60

# 主题常量
TOPIC_AIR = "/air/post"
TOPIC_SOIL = "/soil/post"
TOPIC_IRRIGATION = "strawberry_irrigation"
TOPIC_FAN = "strawberry_fan"


class MqttClient:
    """Yuxi MQTT 客户端（单例），封装 paho-mqtt 异步操作"""

    def __init__(self):
        self._client: mqtt.Client | None = None
        self._air_callback: Callable[[AirSensorData], Awaitable[None]] | None = None
        self._soil_callback: Callable[[SoilSensorData], Awaitable[None]] | None = None
        self._enabled = os.environ.get("MQTT_ENABLED", "false").lower() in ("true", "1")
        self._event_loop = None
        self._connected = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def connected(self) -> bool:
        return self._connected

    def register_air_handler(self, cb: Callable[[AirSensorData], Awaitable[None]]):
        """注册空气传感器数据处理回调"""
        self._air_callback = cb

    def register_soil_handler(self, cb: Callable[[SoilSensorData], Awaitable[None]]):
        """注册土壤传感器数据处理回调"""
        self._soil_callback = cb

    # ---------- 连接管理 ----------

    def connect(self):
        if not self._enabled:
            logger.info("MQTT is disabled (MQTT_ENABLED != true), skipping connection")
            return

        import paho.mqtt.client as mqtt

        self._event_loop = asyncio.get_running_loop()

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=CLIENT_ID
        )
        self._client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        try:
            self._client.connect(BROKER_URL, BROKER_PORT, KEEPALIVE)
            self._client.loop_start()
            logger.info(f"MQTT client connected to {BROKER_URL}:{BROKER_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect MQTT broker: {e}")
            self._enabled = False

    def disconnect(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self._connected = False
            logger.info("MQTT client disconnected")

    # ---------- 订阅 ----------

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self._connected = True
            client.subscribe([(TOPIC_AIR, 1), (TOPIC_SOIL, 1)])
            logger.info(f"MQTT subscribed: {TOPIC_AIR}, {TOPIC_SOIL}")
        else:
            self._connected = False
            logger.error(f"MQTT connection failed with code: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self._connected = False
        if reason_code != 0:
            logger.warning(f"MQTT disconnected unexpectedly, reason_code={reason_code}")
        else:
            logger.info("MQTT disconnected cleanly")

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        logger.info(f"MQTT message received: topic={msg.topic}, payload_len={len(msg.payload)}")

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logger.warning(f"MQTT received invalid JSON on topic {msg.topic}: {msg.payload[:200]}")
            return

        if msg.topic == TOPIC_AIR and self._air_callback:
            asyncio.run_coroutine_threadsafe(self._handle_air(payload), self._event_loop)
        elif msg.topic == TOPIC_SOIL and self._soil_callback:
            asyncio.run_coroutine_threadsafe(self._handle_soil(payload), self._event_loop)
        elif msg.topic not in (TOPIC_AIR, TOPIC_SOIL):
            logger.warning(f"MQTT message on unsubscribed topic: {msg.topic} (expected: {TOPIC_AIR}, {TOPIC_SOIL})")
        elif msg.topic == TOPIC_AIR and not self._air_callback:
            logger.warning("MQTT air data received but no callback registered — data dropped")
        elif msg.topic == TOPIC_SOIL and not self._soil_callback:
            logger.warning("MQTT soil data received but no callback registered — data dropped")

    async def _handle_air(self, payload: dict):
        try:
            data = AirSensorData(**payload)
            if self._air_callback:
                await self._air_callback(data)
        except Exception as e:
            logger.error(f"Failed to handle air sensor data: {e}")

    async def _handle_soil(self, payload: dict):
        try:
            data = SoilSensorData(**payload)
            if self._soil_callback:
                await self._soil_callback(data)
        except Exception as e:
            logger.error(f"Failed to handle soil sensor data: {e}")

    # ---------- 发布（控制指令）----------

    def publish_irrigation(self, cmd: IrrigationCommand) -> bool:
        if not self._client or not self._client.is_connected():
            logger.warning("MQTT not connected, cannot publish irrigation command")
            return False
        self._client.publish(TOPIC_IRRIGATION, cmd.model_dump_json())
        logger.info(f"Published irrigation command: {cmd.action}")
        return True

    def _publish_fan(self, payload: dict) -> bool:
        """统一通过 tomato_fan 发布"""
        if not self._client or not self._client.is_connected():
            logger.warning("MQTT not connected, cannot publish to tomato_fan")
            return False
        data = json.dumps(payload)
        self._client.publish(TOPIC_FAN, data)
        logger.info(f"Published to {TOPIC_FAN}: {data}")
        return True

    def publish_ventilation(self, action: str) -> bool:
        return self._publish_fan({"fan": action})

    def publish_mist(self, action: str) -> bool:
        return self._publish_fan({"water": action})

    def publish_mode(self, mode: str) -> bool:
        return self._publish_fan({"mode": mode})


# 模块级单例
mqtt_client = MqttClient()
