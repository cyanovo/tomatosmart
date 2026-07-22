import { apiGet, apiPost } from './base'

/** 获取 IoT 仪表盘全量数据（空气 + 土壤 + 执行器） */
export function fetchIotDashboard() {
  return apiGet('/api/iot/dashboard')
}

/** 获取最新空气传感器数据 */
export function fetchAirSensor() {
  return apiGet('/api/iot/sensors/air')
}

/** 获取最新土壤传感器数据 */
export function fetchSoilSensor() {
  return apiGet('/api/iot/sensors/soil')
}

/** 控制执行器：key = irrigation | pump | mist | ventilation */
export function setActuator(key, value) {
  return apiPost(`/api/iot/actuators/${key}?value=${value}`)
}

/** 控制 LED 补光灯（支持单路控制） */
export function controlLed(ledCommand) {
  return apiPost('/api/iot/actuators/led', ledCommand)
}

/** 设置工作模式 mode=auto(自主) / mode=ai(AI)，互斥 */
export function setMode(mode) {
  return apiPost(`/api/iot/mode?mode=${mode}`)
}
