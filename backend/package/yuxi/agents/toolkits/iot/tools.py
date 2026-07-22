"""IoT 工具模块 —— 让 Agent 可以读取温室传感器和执行器数据"""

from typing import Annotated

from langchain_core.tools import InjectedToolCallId
from pydantic import BaseModel, Field

from yuxi.agents.toolkits.registry import tool
from yuxi.utils import logger


class GetDashboardInput(BaseModel):
    """获取仪表盘聚合数据"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "传感器", "温室"],
    display_name="获取温室仪表盘数据",
    args_schema=GetDashboardInput,
)
async def get_iot_dashboard(dummy: str = "") -> dict:
    """获取温室 IoT 仪表盘聚合数据，包含空气传感器、土壤传感器和执行器状态。

    这是最常用的查询方式，一次调用获取所有实时数据。
    返回 JSON 包含 air（温湿度/CO2/光照）、soil（pH/EC/氮磷钾/温湿度）、actuators（灌溉/通风/雾化/水泵/LED状态）。

    Returns:
        dict: 聚合仪表盘数据，各字段可能为 null（传感器离线时）
    """
    try:
        from yuxi.services.iot_service import iot_service

        dashboard = await iot_service.get_dashboard()
        if dashboard is None:
            return {"error": "无法获取仪表盘数据"}

        result = {"air": None, "soil": None, "actuators": None}

        if dashboard.air:
            result["air"] = {
                "温度_℃": dashboard.air.temp,
                "湿度_%": dashboard.air.humidity,
                "CO2_ppm": dashboard.air.co2,
                "光照_lx": dashboard.air.illumination,
                "采集时间": dashboard.air.timestamp.isoformat() if dashboard.air.timestamp else "",
            }

        if dashboard.soil:
            result["soil"] = {
                "土壤温度_℃": dashboard.soil.soil_temperature,
                "土壤湿度_%": dashboard.soil.soil_moisture,
                "土壤EC_uS_cm": dashboard.soil.soil_conductivity,
                "pH值": dashboard.soil.ph_value,
                "氮_mg_L": dashboard.soil.nitrogen,
                "磷_mg_L": dashboard.soil.phosphorus,
                "钾_mg_L": dashboard.soil.potassium,
                "采集时间": dashboard.soil.timestamp.isoformat() if dashboard.soil.timestamp else "",
            }

        if dashboard.actuators:
            result["actuators"] = {
                "灌溉": "开启" if dashboard.actuators.irrigation else "关闭",
                "雾化": "开启" if dashboard.actuators.mist else "关闭",
                "通风": "开启" if dashboard.actuators.ventilation else "关闭",
                "水泵": "开启" if dashboard.actuators.pump else "关闭",
                "AI模式": "开启" if dashboard.actuators.ai_mode else "关闭",
                "自动模式": "开启" if dashboard.actuators.auto_mode else "关闭",
                "LED灯": {k: "开启" if v else "关闭" for k, v in dashboard.actuators.leds.items()},
            }

        return result

    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        return {"error": f"获取数据失败: {str(e)}"}


class GetAirSensorsInput(BaseModel):
    """获取空气传感器数据"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "传感器", "空气"],
    display_name="获取空气传感器数据",
    args_schema=GetAirSensorsInput,
)
async def get_air_sensors(dummy: str = "") -> dict:
    """获取温室空气传感器最新数据：温度、湿度、CO2浓度、光照强度。

    Returns:
        dict: 空气传感器读数，包含温度(°C)、湿度(%)、CO2(ppm)、光照(lx)和采集时间
    """
    try:
        from yuxi.services.iot_service import iot_service

        data = await iot_service.get_latest_air()
        if data is None:
            return {"error": "空气传感器离线，暂无数据"}

        return {
            "温度_℃": data.temp,
            "湿度_%": data.humidity,
            "CO2_ppm": data.co2,
            "光照_lx": data.illumination,
            "采集时间": data.timestamp.isoformat() if data.timestamp else "",
        }

    except Exception as e:
        logger.error(f"获取空气传感器失败: {e}")
        return {"error": f"获取失败: {str(e)}"}


class GetSoilSensorsInput(BaseModel):
    """获取土壤传感器数据"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "传感器", "土壤"],
    display_name="获取土壤传感器数据",
    args_schema=GetSoilSensorsInput,
)
async def get_soil_sensors(dummy: str = "") -> dict:
    """获取温室土壤/水培传感器最新数据：pH值、EC、氮磷钾、温湿度。

    Returns:
        dict: 土壤传感器读数
    """
    try:
        from yuxi.services.iot_service import iot_service

        data = await iot_service.get_latest_soil()
        if data is None:
            return {"error": "土壤传感器离线，暂无数据"}

        return {
            "土壤温度_℃": data.soil_temperature,
            "土壤湿度_%": data.soil_moisture,
            "电导率_uS_cm": data.soil_conductivity,
            "pH值": data.ph_value,
            "氮_mg_L": data.nitrogen,
            "磷_mg_L": data.phosphorus,
            "钾_mg_L": data.potassium,
            "采集时间": data.timestamp.isoformat() if data.timestamp else "",
        }

    except Exception as e:
        logger.error(f"获取土壤传感器失败: {e}")
        return {"error": f"获取失败: {str(e)}"}


# ---------- 执行器控制工具 ----------

CONTROL_KEYS = ["irrigation", "mist", "ventilation", "pump"]


class ControlActuatorInput(BaseModel):
    """执行器控制输入"""

    key: str = Field(description=f"执行器名称，可选: {', '.join(CONTROL_KEYS)}")
    value: bool = Field(description="true=开启, false=关闭")


@tool(
    category="buildin",
    tags=["IoT", "执行器", "控制"],
    display_name="控制执行器开关",
    args_schema=ControlActuatorInput,
)
async def control_actuator(key: str, value: bool) -> dict:
    """控制温室执行器的开关状态（灌溉/雾化/通风/水泵）。

    使用前必须先通过 get_iot_dashboard 或 get_actuators 确认当前状态，
    结合传感器数据判断是否需要操作。

    Args:
        key: 执行器名称（irrigation/mist/ventilation/pump）
        value: true=开启, false=关闭

    Returns:
        dict: {"ok": true/false, "key": "...", "value": true/false, "message": "..."}
    """
    if key not in CONTROL_KEYS:
        return {"ok": False, "key": key, "message": f"未知执行器，可选: {', '.join(CONTROL_KEYS)}"}

    try:
        from yuxi.services.iot_service import iot_service

        ok = await iot_service.control_actuator(key, value)
        name_map = {"irrigation": "灌溉", "mist": "雾化", "ventilation": "通风", "pump": "水泵"}
        action = "开启" if value else "关闭"
        if ok:
            return {"ok": True, "key": key, "value": value, "message": f"{name_map[key]}已{action}"}
        else:
            return {"ok": False, "key": key, "value": value, "message": f"{name_map[key]}{action}失败，请检查MQTT连接"}
    except Exception as e:
        logger.error(f"控制执行器失败: {e}")
        return {"ok": False, "key": key, "message": f"控制失败: {str(e)}"}


class SetIotModeInput(BaseModel):
    """模式切换输入"""

    mode: str = Field(description="目标模式: auto(自主模式) 或 ai(AI模式)")


@tool(
    category="buildin",
    tags=["IoT", "模式", "控制"],
    display_name="切换IoT工作模式",
    args_schema=SetIotModeInput,
)
async def set_iot_mode(mode: str) -> dict:
    """切换温室 IoT 系统的工作模式。

    - auto: 自主模式，按预设阈值自动控制
    - ai: AI 模式，由AI根据实时数据分析决策

    Args:
        mode: "auto" 或 "ai"

    Returns:
        dict: {"ok": true/false, "mode": "...", "message": "..."}
    """
    if mode not in ("auto", "ai"):
        return {"ok": False, "mode": mode, "message": "无效模式，可选: auto, ai"}

    try:
        from yuxi.services.iot_service import iot_service

        ok = await iot_service.set_mode(mode)
        if ok:
            return {"ok": True, "mode": mode, "message": f"已切换到{'AI智能' if mode == 'ai' else '自主'}模式"}
        else:
            return {"ok": False, "mode": mode, "message": "模式切换失败，请检查MQTT连接"}
    except Exception as e:
        logger.error(f"切换模式失败: {e}")
        return {"ok": False, "mode": mode, "message": f"切换失败: {str(e)}"}


class GetActuatorsInput(BaseModel):
    """获取执行器状态"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "执行器", "控制"],
    display_name="获取执行器状态",
    args_schema=GetActuatorsInput,
)
async def get_actuators(dummy: str = "") -> dict:
    """获取温室执行器（灌溉/通风/雾化/水泵/LED/模式）的当前开关状态。

    Returns:
        dict: 各执行器的开启/关闭状态
    """
    try:
        from yuxi.services.iot_service import iot_service

        data = await iot_service.get_actuator_status()
        if data is None:
            return {"error": "无法获取执行器状态"}

        return {
            "灌溉": "开启" if data.irrigation else "关闭",
            "雾化": "开启" if data.mist else "关闭",
            "通风": "开启" if data.ventilation else "关闭",
            "水泵": "开启" if data.pump else "关闭",
            "AI模式": "开启" if data.ai_mode else "关闭",
            "自动模式": "开启" if data.auto_mode else "关闭",
            "LED灯": {k: "开启" if v else "关闭" for k, v in data.leds.items()},
        }

    except Exception as e:
        logger.error(f"获取执行器状态失败: {e}")
        return {"error": f"获取失败: {str(e)}"}
