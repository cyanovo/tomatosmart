from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.utils.auth_middleware import get_required_user
from yuxi.iot.schemas import IotDashboardData, LedCommand
from yuxi.services.iot_service import iot_service

iot = APIRouter(prefix="/iot", tags=["IoT 智能温室"])


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
    """控制执行器：key = irrigation | pump | mist | ventilation, value = true/false"""
    ok = await iot_service.control_actuator(key, value)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "key": key, "value": value}


@iot.post("/actuators/led")
async def control_led(cmd: LedCommand, _=Depends(get_required_user)):
    """控制 LED 补光灯 — 仅传需要变更的通道，如 {"led3":"on"}"""
    ok = await iot_service.control_led(cmd)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True}


@iot.post("/mode")
async def set_mode(mode: str = "auto", _=Depends(get_required_user)):
    """设置工作模式 — mode=auto(自主) / mode=ai(AI)，互斥，通过 MQTT 下发"""
    if mode not in ("auto", "ai"):
        raise HTTPException(status_code=400, detail="mode 只能为 auto 或 ai")
    ok = await iot_service.set_mode(mode)
    if not ok:
        raise HTTPException(status_code=503, detail="MQTT 不可用或指令发送失败")
    return {"ok": True, "mode": mode}
