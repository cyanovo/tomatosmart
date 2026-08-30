from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from server.utils.auth_middleware import get_required_user
from yuxi.iot.schemas import IotDashboardData, LedCommand
from yuxi.services.iot_service import iot_service

iot = APIRouter(prefix="/iot", tags=["IoT 智能温室"])


class RestScheduleRequest(BaseModel):
    start_hour: int = Field(ge=0, le=23)
    start_minute: int = Field(ge=0, le=59)
    end_hour: int = Field(ge=0, le=23)
    end_minute: int = Field(ge=0, le=59)


@iot.get("/dashboard", response_model=IotDashboardData)
async def get_dashboard(_=Depends(get_required_user)):
    """获取 IoT 仪表盘全部实时数据（空气 + 土壤 + 执行器状态）"""
    return await iot_service.get_dashboard()


@iot.get("/sensors/air")
async def get_air_sensor(_=Depends(get_required_user)):
    """获取最新空气传感器数据"""
    data = await iot_service.get_latest_air()
    if data is None:
        raise HTTPException(status_code=404, detail="暂无空气传感器数据")
    return data


@iot.get("/sensors/soil")
async def get_soil_sensor(_=Depends(get_required_user)):
    """获取最新土壤传感器数据"""
    data = await iot_service.get_latest_soil()
    if data is None:
        raise HTTPException(status_code=404, detail="暂无土壤传感器数据")
    return data


@iot.post("/actuators/{key}")
async def set_actuator(key: str, value: bool, _=Depends(get_required_user)):
    """控制执行器：key = irrigation | pump, value = true/false"""
    ok = await iot_service.control_actuator(key, value)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "key": key, "value": value}


@iot.post("/light/red")
async def set_red_brightness(value: int, _=Depends(get_required_user)):
    """设置红光亮度：0-100，对应 MQTT cmd 01"""
    if value < 0 or value > 100:
        raise HTTPException(status_code=400, detail="value 必须在 0-100 之间")
    ok = await iot_service.set_red_brightness(value)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "value": value}


@iot.post("/light/blue")
async def set_blue_brightness(value: int, _=Depends(get_required_user)):
    """设置蓝光亮度：0-100，对应 MQTT cmd 02"""
    if value < 0 or value > 100:
        raise HTTPException(status_code=400, detail="value 必须在 0-100 之间")
    ok = await iot_service.set_blue_brightness(value)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "value": value}


@iot.post("/light/mode")
async def set_fill_light_mode(value: int, _=Depends(get_required_user)):
    """设置番茄补光模式：1-5，对应 MQTT cmd 05"""
    if value < 1 or value > 5:
        raise HTTPException(status_code=400, detail="value 必须在 1-5 之间")
    ok = await iot_service.set_fill_light_mode(value)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "value": value}


@iot.post("/pump/interval")
async def set_pump_interval(value: int, _=Depends(get_required_user)):
    """设置水泵工作间隔分钟：0-65535，对应 MQTT cmd 06"""
    if value < 0 or value > 65535:
        raise HTTPException(status_code=400, detail="value 必须在 0-65535 之间")
    ok = await iot_service.set_pump_interval(value)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "value": value}


@iot.post("/pump/duration")
async def set_pump_duration(value: int, _=Depends(get_required_user)):
    """设置水泵单次工作秒数：0-65535，对应 MQTT cmd 07"""
    if value < 0 or value > 65535:
        raise HTTPException(status_code=400, detail="value 必须在 0-65535 之间")
    ok = await iot_service.set_pump_duration(value)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "value": value}


@iot.post("/rest-schedule")
async def set_rest_schedule(body: RestScheduleRequest, _=Depends(get_required_user)):
    """设置休息开始和结束时间，对应 MQTT cmd 09"""
    ok = await iot_service.set_rest_schedule(
        body.start_hour,
        body.start_minute,
        body.end_hour,
        body.end_minute,
    )
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, **body.model_dump()}


@iot.post("/actuators/led")
async def control_led(cmd: LedCommand, _=Depends(get_required_user)):
    """控制 LED 补光灯 — 旧多路接口映射为新版总灯开关"""
    ok = await iot_service.control_led(cmd)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True}


@iot.post("/mode")
async def set_mode(mode: str = "auto", _=Depends(get_required_user)):
    """设置工作模式 — mode=manual(手动) / ai(AI)，兼容旧 auto 参数"""
    if mode == "auto":
        mode = "manual"
    if mode not in ("manual", "ai"):
        raise HTTPException(status_code=400, detail="mode 只能为 manual 或 ai")
    ok = await iot_service.set_mode(mode)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "mode": mode}
