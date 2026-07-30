/**
 * 番茄成熟度检测 API
 *
 * 支持两种模式:
 * 1. Docker 后端 (历史记录等): /api/detect/*
 * 2. 本地检测服务 (摄像头检测): /detect-api/*
 */

/**
 * 获取认证头
 */
function getAuthHeaders() {
  const token = localStorage.getItem('user_token') || ''
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`
  }
}

/**
 * 拍照并执行成熟度检测（调用本地检测服务）
 * @param {Object} params
 * @param {string} params.zone - 棚区 (A/B/C)
 * @param {number} [params.camera_id] - 摄像头 ID
 * @param {number} [params.conf_threshold] - 置信度阈值
 */
export async function captureAndDetect(params = {}) {
  const res = await fetch('/detect-api/detect/camera', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(params),
  })
  if (!res.ok) throw new Error(`检测失败: ${res.status}`)
  return res.json()
}

/**
 * 上传图片进行检测（调用本地检测服务）
 * @param {File} file - 图片文件
 * @param {string} zone - 棚区
 * @param {number} [conf_threshold] - 置信度阈值
 */
export async function detectFromImage(file, zone = 'A', conf_threshold) {
  const formData = new FormData()
  formData.append('file', file)

  let url = `/detect-api/detect/image?zone=${zone}`
  if (conf_threshold !== undefined) {
    url += `&conf_threshold=${conf_threshold}`
  }

  const token = localStorage.getItem('user_token') || ''
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!res.ok) throw new Error(`检测失败: ${res.status}`)
  return res.json()
}

/**
 * 查询检测历史（调用 Docker 后端）
 * @param {Object} params
 * @param {string} [params.zone] - 棚区筛选
 * @param {number} [params.limit] - 返回数量
 */
export async function getDetectHistory(params = {}) {
  const query = new URLSearchParams()
  if (params.zone) query.set('zone', params.zone)
  if (params.limit) query.set('limit', String(params.limit))

  const res = await fetch(`/api/detect/history?${query.toString()}`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`查询失败: ${res.status}`)
  return res.json()
}

/**
 * 获取各区域成熟度统计（调用 Docker 后端）
 */
export async function getDetectStats() {
  const res = await fetch('/api/detect/stats', {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`查询失败: ${res.status}`)
  return res.json()
}

/**
 * 获取摄像头状态（调用本地检测服务）
 */
export async function getCameraStatus() {
  const res = await fetch('/detect-api/health', {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`查询失败: ${res.status}`)
  return res.json()
}

/**
 * 列出所有可用摄像头（调用本地检测服务）
 */
export async function listCameras() {
  const res = await fetch('/detect-api/cameras', {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`查询失败: ${res.status}`)
  return res.json()
}

