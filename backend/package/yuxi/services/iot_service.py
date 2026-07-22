from __future__ import annotations

import asyncio
import json

from yuxi.iot.mqtt_client import mqtt_client
from yuxi.iot.schemas import (
    ActuatorStatus,
    AirSensorData,
    IotDashboardData,
    IrrigationCommand,
    LedCommand,
    SoilSensorData,
)
from yuxi.services.run_queue_service import get_redis_client
from yuxi.utils import logger


class IotService:
    """IoT 业务服务（单例 — 由 lifespan 初始化回调）"""

    KEY_AIR = "iot:latest:air"
    KEY_SOIL = "iot:latest:soil"
    KEY_ACTUATORS = "iot:actuators"

    def __init__(self):
        self._redis = None

    async def _ensure_redis(self):
        if self._redis is None:
            self._redis = await get_redis_client()

    # ---------- 传感器数据处理（MQTT 回调）----------

    async def on_air_data(self, data: AirSensorData):
        await self._ensure_redis()
        await self._redis.set(self.KEY_AIR, data.model_dump_json())
        logger.debug(f"Air sensor data updated: {data.temp}°C, {data.humidity}%")

    async def on_soil_data(self, data: SoilSensorData):
        await self._ensure_redis()
        await self._redis.set(self.KEY_SOIL, data.model_dump_json())
        logger.debug(f"Soil sensor data updated: {data.soil_moisture}%")

    # ---------- 数据查询 ----------

    async def get_latest_air(self) -> AirSensorData | None:
        await self._ensure_redis()
        raw = await self._redis.get(self.KEY_AIR)
        if not raw:
            logger.debug(f"No air sensor data in Redis (key={self.KEY_AIR})")
            return None
        try:
            data = AirSensorData(**json.loads(raw))
            logger.debug(f"Air sensor data loaded: {data.temp}°C, {data.humidity}%")
            return data
        except Exception as e:
            logger.error(f"Failed to parse air sensor data from Redis (raw={raw[:200]}): {e}")
            return None

    async def get_latest_soil(self) -> SoilSensorData | None:
        await self._ensure_redis()
        raw = await self._redis.get(self.KEY_SOIL)
        if not raw:
            logger.debug(f"No soil sensor data in Redis (key={self.KEY_SOIL})")
            return None
        try:
            data = SoilSensorData(**json.loads(raw))
            logger.debug(f"Soil sensor data loaded: moisture={data.soil_moisture}%")
            return data
        except Exception as e:
            logger.error(f"Failed to parse soil sensor data from Redis (raw={raw[:200]}): {e}")
            return None

    async def get_actuator_status(self) -> ActuatorStatus:
        await self._ensure_redis()
        raw = await self._redis.get(self.KEY_ACTUATORS)
        if raw:
            return ActuatorStatus(**json.loads(raw))
        return ActuatorStatus()

    async def get_dashboard(self) -> IotDashboardData:
        air, soil, actuators = await asyncio.gather(
            self.get_latest_air(),
            self.get_latest_soil(),
            self.get_actuator_status(),
        )
        dashboard = IotDashboardData(air=air, soil=soil, actuators=actuators)
        logger.debug(
            f"IoT dashboard: air={'present' if air else 'missing'}, "
            f"soil={'present' if soil else 'missing'}, "
            f"actuators={actuators.model_dump_json()}"
        )
        return dashboard

    # ---------- 执行器控制 ----------

    async def start_irrigation(self) -> bool:
        ok = mqtt_client.publish_irrigation(IrrigationCommand(action="start"))
        if ok:
            await self._update_actuator("irrigation", True)
            await self._update_actuator("pump", True)
        return ok

    async def stop_irrigation(self) -> bool:
        ok = mqtt_client.publish_irrigation(IrrigationCommand(action="stop"))
        if ok:
            await self._update_actuator("irrigation", False)
            await self._update_actuator("pump", False)
        return ok

    async def control_actuator(self, key: str, value: bool) -> bool:
        """通用执行器控制 — 用于前端 Switch"""
        match key:
            case "irrigation":
                return await (self.start_irrigation() if value else self.stop_irrigation())
            case "pump":
                if value:
                    return await self.start_irrigation()
                else:
                    return await self.stop_irrigation()
            case "mist":
                ok = mqtt_client.publish_mist("on" if value else "off")
                if ok:
                    await self._update_actuator(key, value)
                return ok
            case "ventilation":
                ok = mqtt_client.publish_ventilation("on" if value else "off")
                if ok:
                    await self._update_actuator(key, value)
                return ok
            case _:
                logger.warning(f"Unknown actuator key: {key}")
                return False

    # ---------- 模式控制 ----------

    async def set_mode(self, mode: str) -> bool:
        """设置工作模式 — AI 和自主互斥，通过 MQTT 下发到硬件"""
        ok = mqtt_client.publish_mode(mode)
        if ok:
            current = await self.get_actuator_status()
            current.ai_mode = (mode == "ai")
            current.auto_mode = (mode == "auto")
            await self._redis.set(self.KEY_ACTUATORS, current.model_dump_json())
        return ok

    async def _update_actuator(self, key: str, value: bool):
        await self._ensure_redis()
        status = await self.get_actuator_status()
        setattr(status, key, value)
        await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())

    async def _persist_led_state(self, cmd: LedCommand):
        await self._ensure_redis()
        status = await self.get_actuator_status()
        for led_name in ("led1", "led2", "led3", "led4", "led5"):
            val = getattr(cmd, led_name, None)
            if val is not None:
                status.leds[led_name] = val == "on"
        await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())


# 模块级单例
iot_service = IotService()
