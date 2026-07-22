from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---- 传感器数据模型 ----


class AirSensorData(BaseModel):
    """空气传感器数据（对应 /air/post 发布的消息）"""

    humidity: float = Field(..., description="空气湿度（%）")
    temp: float = Field(..., description="空气温度（℃）")
    co2: int = Field(..., description="CO2 浓度（ppm）")
    illumination: float = Field(
        default=0,
        alias="Illumination",
        serialization_alias="illumination",
        description="光照强度（lux）",
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="接收时间")


class SoilSensorData(BaseModel):
    """土壤传感器数据（对应 /soil/post 发布的消息）"""

    soil_moisture: float = Field(..., description="土壤湿度（%）")
    soil_temperature: float = Field(..., description="土壤温度（℃）")
    soil_conductivity: float = Field(..., description="土壤电导率（μS/cm）")
    ph_value: float = Field(..., description="pH 值")
    nitrogen: float = Field(..., description="氮含量")
    phosphorus: float = Field(..., description="磷含量")
    potassium: float = Field(..., description="钾含量")
    timestamp: datetime = Field(default_factory=datetime.now, description="接收时间")


# ---- 执行器指令模型 ----


class IrrigationCommand(BaseModel):
    """灌溉控制指令（发布到 strawberry_irrigation）"""

    action: Literal["start", "stop"]


class LedCommand(BaseModel):
    """LED 补光灯控制指令（发布到 strawberry_fan）"""

    led1: Literal["on", "off"] | None = None
    led2: Literal["on", "off"] | None = None
    led3: Literal["on", "off"] | None = None
    led4: Literal["on", "off"] | None = None
    led5: Literal["on", "off"] | None = None


# ---- 聚合响应模型 ----


class ActuatorStatus(BaseModel):
    """执行器当前状态"""

    irrigation: bool = False  # 灌溉
    mist: bool = False  # 水雾培
    ventilation: bool = False  # 通风
    pump: bool = False  # 水泵
    ai_mode: bool = False  # AI 模式
    auto_mode: bool = True  # 自主模式（默认开启）
    leds: dict[str, bool] = Field(
        default_factory=lambda: {
            "led1": False,
            "led2": False,
            "led3": False,
            "led4": False,
            "led5": False,
        }
    )


class IotDashboardData(BaseModel):
    """IoT 仪表盘聚合数据 — 前端单次查询即可获取全部实时数据"""

    air: AirSensorData | None = None
    soil: SoilSensorData | None = None
    actuators: ActuatorStatus = Field(default_factory=ActuatorStatus)
