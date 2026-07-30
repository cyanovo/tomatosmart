<template>
  <div class="maturity-center layout-container">
    <PageHeader title="成熟度管理中心" :show-border="true">
      <template #info>
        <PageAgentDropdown default-agent="maturity-analyzer" />
        <span class="threshold-config">
          <span>采摘阈值</span>
          <input
            type="number"
            class="threshold-input"
            v-model.number="harvestThreshold"
            min="0" max="100"
            @change="persistThreshold"
          />
          <span>%</span>
        </span>
        <span class="status-pill" :class="cameraReady ? 'online' : 'offline'">
          <Camera :size="14" />
          {{ cameraReady ? '摄像头就绪' : '摄像头未连接' }}
        </span>
      </template>
    </PageHeader>

    <main class="maturity-content">
      <!-- 检测操作区 -->
      <section class="detect-action-bar">
        <div class="action-left">
          <div class="zone-selector">
            <span>棚区</span>
            <button
              v-for="z in zones"
              :key="z.id"
              :class="{ active: selectedZone === z.id }"
              @click="selectedZone = z.id"
            >{{ z.name }}</button>
          </div>
          <div class="camera-selector">
            <span>摄像头</span>
            <select v-model="selectedCameraId" :disabled="detecting || cameraActive">
              <option v-if="!availableCameras.length" :value="-1">未检测到摄像头</option>
              <option
                v-for="cam in availableCameras"
                :key="cam.id"
                :value="cam.id"
              >{{ cam.name }}</option>
            </select>
          </div>
        </div>
        <div class="action-right">
          <button
            class="preview-btn"
            :class="{ active: cameraActive }"
            @click="toggleCamera"
          >
            <Video :size="16" />
            {{ cameraActive ? '关闭摄像头' : '开启摄像头' }}
          </button>
          <button
            class="capture-btn"
            :disabled="detecting || !cameraActive"
            @click="doCapture"
          >
            <Camera :size="18" />
            {{ detecting ? '检测中...' : '拍照检测' }}
          </button>
        </div>
      </section>

      <!-- 摄像头预览 + 检测结果 -->
      <section class="preview-result-section">
        <!-- 左侧：摄像头预览 -->
        <div class="camera-panel">
          <div class="panel-header">
            <div class="section-title">
              <Camera :size="18" />
              <h3>摄像头画面</h3>
            </div>
          </div>
          <div class="video-container">
            <video
              ref="videoRef"
              autoplay
              playsinline
              muted
              class="camera-video"
              v-show="cameraActive"
            ></video>
            <canvas ref="canvasRef" style="display: none;"></canvas>
            <div class="camera-placeholder" v-if="!cameraActive">
              <Camera :size="48" />
              <p>点击"开启摄像头"开始</p>
            </div>
          </div>
        </div>

        <!-- 右侧：检测结果 -->
        <div class="result-panel">
          <div class="panel-header">
            <div class="section-title">
              <ScanLine :size="18" />
              <h3>检测结果</h3>
            </div>
            <span class="result-time" v-if="latestResult">{{ formatTime(latestResult.created_at) }}</span>
          </div>

          <!-- 检测中状态 -->
          <div class="detecting-state" v-if="detecting">
            <div class="loading-spinner"></div>
            <p>正在识别中...</p>
          </div>

          <!-- 检测结果 -->
          <div class="result-content" v-else-if="latestResult">
            <div class="annotated-image-wrapper">
              <img
                :src="'data:image/jpeg;base64,' + latestResult.annotated_image_base64"
                alt="检测标注图"
                class="annotated-image"
              />
            </div>
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-label">总数</span>
                <strong>{{ latestResult.total_count }}</strong>
              </div>
              <div class="stat-item ripe">
                <span class="stat-label">成熟</span>
                <strong>{{ latestResult.ripe_count }}</strong>
              </div>
              <div class="stat-item half">
                <span class="stat-label">半成熟</span>
                <strong>{{ latestResult.half_ripe_count }}</strong>
              </div>
              <div class="stat-item unripe">
                <span class="stat-label">未成熟</span>
                <strong>{{ latestResult.unripe_count }}</strong>
              </div>
            </div>
            <div class="maturity-bar">
              <div class="bar-header">
                <span>成熟度</span>
                <strong :class="{ ready: latestResult.maturity_ratio >= harvestThreshold }">{{ latestResult.maturity_ratio }}%</strong>
              </div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: latestResult.maturity_ratio + '%' }" :class="{ ready: latestResult.maturity_ratio >= harvestThreshold }"></div>
                <div class="bar-threshold" :style="{ left: harvestThreshold + '%' }"></div>
              </div>
            </div>
            <div class="recommendation">
              <ClipboardCheck :size="16" />
              <span>{{ latestResult.recommendation }}</span>
            </div>
          </div>

          <!-- 空状态 -->
          <div class="empty-state" v-else>
            <ScanLine :size="48" />
            <p>开启摄像头后点击"拍照检测"</p>
          </div>
        </div>
      </section>

      <!-- 汇总卡片 -->
      <section class="summary-grid">
        <article v-for="item in summary" :key="item.label" class="summary-card">
          <component :is="item.icon" :size="20" />
          <div>
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.note }}</p>
          </div>
        </article>
      </section>

      <!-- 历史记录 + 采摘建议 -->
      <section class="records-layout">
        <article class="scan-panel">
          <div class="section-title">
            <Route :size="18" />
            <h3>检测记录</h3>
          </div>
          <div class="scan-list" v-if="historyRecords.length">
            <div v-for="record in historyRecords" :key="record.id" class="scan-row">
              <div class="scan-main">
                <strong>{{ getZoneName(record.zone) }} · 检测 #{{ record.id.slice(-6) }}</strong>
                <span>{{ formatTime(record.created_at) }}</span>
              </div>
              <div class="scan-numbers">
                <span>{{ record.total_count }} 颗</span>
                <strong :class="{ ready: record.maturity_ratio >= harvestThreshold }">{{ record.maturity_ratio }}%</strong>
              </div>
              <span class="scan-advice" :class="{ ready: record.maturity_ratio >= harvestThreshold }">
                {{ record.maturity_ratio >= harvestThreshold ? '可采摘' : '继续观察' }}
              </span>
            </div>
          </div>
          <div v-else class="empty-hint">
            <Camera :size="32" />
            <p>暂无检测记录，点击"拍照检测"开始</p>
          </div>
        </article>

        <article class="advice-panel">
          <div class="section-title">
            <ClipboardCheck :size="18" />
            <h3>采摘建议</h3>
          </div>
          <div class="advice-list">
            <div v-for="advice in displayAdvice" :key="advice.title" class="advice-item">
              <span class="advice-level" :class="advice.level">{{ advice.levelText }}</span>
              <div>
                <strong>{{ advice.title }}</strong>
                <p>{{ advice.desc }}</p>
              </div>
            </div>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Camera,
  ClipboardCheck,
  Gauge,
  Route,
  ScanLine,
  Sprout,
  Timer,
  Video
} from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import PageAgentDropdown from '@/components/PageAgentDropdown.vue'
import { getHarvestThreshold, setHarvestThreshold } from '@/data/tomatoData.js'
import { captureAndDetect, getDetectHistory, listCameras } from '@/apis/detect_api.js'

const router = useRouter()

// 棚区配置
const zones = [
  { id: 'A', name: 'A 区' },
  { id: 'B', name: 'B 区' },
  { id: 'C', name: 'C 区' }
]

// 状态
const selectedZone = ref('A')
const harvestThreshold = ref(getHarvestThreshold())
const cameraReady = ref(false)
const cameraActive = ref(false)
const detecting = ref(false)
const latestResult = ref(null)
const historyRecords = ref([])
const availableCameras = ref([])
const selectedCameraId = ref(0)

// DOM refs
const videoRef = ref(null)
const canvasRef = ref(null)

// 当前媒体流
let currentStream = null

function persistThreshold() {
  const n = harvestThreshold.value
  if (n >= 0 && n <= 100) setHarvestThreshold(n)
}

function getZoneName(zoneId) {
  return zones.find(z => z.id === zoneId)?.name || zoneId
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const time = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return isToday ? `今天 ${time}` : `${d.getMonth() + 1}/${d.getDate()} ${time}`
}

// 开启/关闭摄像头
async function toggleCamera() {
  if (cameraActive.value) {
    stopCamera()
  } else {
    await startCamera()
  }
}

async function startCamera() {
  try {
    // 停止之前的流
    stopCamera()

    // 获取摄像头
    const constraints = {
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'environment'  // 优先使用后置摄像头
      }
    }

    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    currentStream = stream

    if (videoRef.value) {
      videoRef.value.srcObject = stream
      cameraActive.value = true
      cameraReady.value = true
    }
  } catch (err) {
    console.error('无法访问摄像头:', err)
    alert('无法访问摄像头，请确保已授权摄像头权限')
  }
}

function stopCamera() {
  if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop())
    currentStream = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  cameraActive.value = false
}

// 拍照检测
async function doCapture() {
  if (!cameraActive.value || !videoRef.value || !canvasRef.value) {
    alert('请先开启摄像头')
    return
  }

  detecting.value = true

  try {
    // 从视频捕获帧
    const video = videoRef.value
    const canvas = canvasRef.value
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    // 转为 Blob
    const blob = await new Promise(resolve => {
      canvas.toBlob(resolve, 'image/jpeg', 0.9)
    })

    // 上传检测
    const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' })
    const result = await detectFromImage(file, selectedZone.value, 0.5)
    latestResult.value = result

    // 刷新历史
    await loadHistory()
  } catch (e) {
    console.error('检测失败:', e)
    alert('检测失败: ' + e.message)
  } finally {
    detecting.value = false
  }
}

// 上传图片检测
async function detectFromImage(file, zone = 'A', conf_threshold = 0.5) {
  const formData = new FormData()
  formData.append('file', file)

  const token = localStorage.getItem('user_token') || ''
  const res = await fetch(`/detect-api/detect/image?zone=${zone}&conf_threshold=${conf_threshold}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })

  if (!res.ok) throw new Error(`检测失败: ${res.status}`)
  return res.json()
}

// 加载历史
async function loadHistory() {
  try {
    historyRecords.value = await getDetectHistory({ limit: 20 })
  } catch (e) {
    console.error('加载历史失败:', e)
  }
}

// 汇总卡片
const summary = computed(() => {
  const r = latestResult.value
  if (!r) {
    return [
      { label: '本次识别总数', value: '—', note: '等待检测', icon: Sprout },
      { label: '平均成熟度', value: '—', note: '等待检测', icon: Gauge },
      { label: '建议采摘量', value: '—', note: '等待检测', icon: Timer },
      { label: '检测状态', value: '就绪', note: cameraReady.value ? '摄像头已连接' : '摄像头未连接', icon: ScanLine }
    ]
  }
  const yieldKg = Math.round(r.ripe_count * 0.1)
  return [
    { label: '本次识别总数', value: `${r.total_count} 颗`, note: `${getZoneName(r.zone)} 检测`, icon: Sprout },
    { label: '平均成熟度', value: `${r.maturity_ratio}%`, note: r.maturity_ratio >= harvestThreshold.value ? '达到采摘阈值' : '未达阈值', icon: Gauge },
    { label: '建议采摘量', value: `${yieldKg} kg`, note: `${r.ripe_count} 颗成熟果`, icon: Timer },
    { label: '检测状态', value: '完成', note: `阈值 ${r.confidence_threshold}`, icon: ScanLine }
  ]
})

// 采摘建议
const displayAdvice = computed(() => {
  const r = latestResult.value
  const items = []

  if (r) {
    const zn = getZoneName(r.zone)
    if (r.maturity_ratio >= harvestThreshold.value) {
      items.push({ level: 'ready', levelText: '执行', title: `${zn} 成熟度 ${r.maturity_ratio}%`, desc: '已达采摘阈值，建议立即采摘。' })
    } else if (r.maturity_ratio >= harvestThreshold.value - 10) {
      items.push({ level: 'watch', levelText: '观察', title: `${zn} 接近采摘窗口`, desc: `成熟度 ${r.maturity_ratio}%，建议明天再次检测。` })
    } else {
      items.push({ level: 'normal', levelText: '正常', title: `${zn} 未达采摘阈值`, desc: '继续观察，维持当前策略。' })
    }
  }

  const latestZone = latestResult.value?.zone
  for (const z of zones) {
    if (z.id === latestZone) continue
    const zoneRecords = historyRecords.value.filter(r => r.zone === z.id)
    if (zoneRecords.length) {
      const latest = zoneRecords[0]
      if (latest.maturity_ratio >= harvestThreshold.value) {
        items.push({ level: 'ready', levelText: '执行', title: `${z.name} 成熟度 ${latest.maturity_ratio}%`, desc: '已达采摘阈值。' })
      } else {
        items.push({ level: 'normal', levelText: '正常', title: `${z.name} 成熟度 ${latest.maturity_ratio}%`, desc: '继续观察。' })
      }
    } else {
      items.push({ level: 'normal', levelText: '待检测', title: `${z.name} 暂无数据`, desc: '请使用摄像头检测该区域。' })
    }
  }

  return items
})

// 初始化
onMounted(async () => {
  // 加载摄像头列表（用于显示）
  try {
    const cameras = await listCameras()
    availableCameras.value = cameras || []
    if (cameras.length > 0) {
      selectedCameraId.value = cameras[0].id
      cameraReady.value = true
    }
  } catch {
    // 即使获取列表失败，也可以使用浏览器摄像头
    availableCameras.value = [{ id: 0, name: '默认摄像头' }]
    selectedCameraId.value = 0
  }
  // 加载历史
  await loadHistory()
})

// 清理
onUnmounted(() => {
  stopCamera()
})
</script>

<style scoped lang="less">
.maturity-center {
  min-height: 100%;
  background: var(--gray-25);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;

  &.online {
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
  &.offline {
    background: var(--color-error-50);
    color: var(--color-error-700);
  }
}

.maturity-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--page-padding);
}

/* 检测操作栏 */
.detect-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.action-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.action-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.zone-selector, .camera-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--gray-600);

  button {
    min-width: 48px;
    height: 28px;
    padding: 0 10px;
    border: 1px solid var(--gray-200);
    border-radius: 6px;
    background: var(--gray-0);
    color: var(--gray-700);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover { border-color: var(--main-color); color: var(--main-color); }
    &.active {
      border-color: var(--main-color);
      background: var(--main-50);
      color: var(--main-color);
      font-weight: 600;
    }
  }
}

.camera-selector select {
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 13px;
  cursor: pointer;
  outline: none;

  &:focus { border-color: var(--main-color); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.preview-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--main-color);
    color: var(--main-color);
  }

  &.active {
    border-color: var(--color-success-500);
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
}

.capture-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
  height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) { opacity: 0.9; }
  &:disabled {
    background: var(--gray-200);
    color: var(--gray-500);
    cursor: not-allowed;
  }
}

/* 预览+结果区域 */
.preview-result-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-height: 400px;
}

.camera-panel, .result-panel {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--gray-150);
}

.result-time {
  color: var(--gray-500);
  font-size: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--main-color);

  h3 {
    margin: 0;
    color: var(--gray-1000);
    font-size: 15px;
    font-weight: 650;
  }
}

/* 视频容器 */
.video-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  min-height: 300px;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--gray-400);

  p {
    margin: 0;
    font-size: 14px;
  }
}

/* 检测结果 */
.detecting-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--main-color);

  p {
    margin: 0;
    font-size: 14px;
  }
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--gray-200);
  border-top-color: var(--main-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.result-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 14px;
}

.annotated-image-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-10);
  border-radius: 6px;
  overflow: hidden;
  min-height: 200px;
}

.annotated-image {
  max-width: 100%;
  max-height: 220px;
  object-fit: contain;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px;
  border-radius: 6px;
  background: var(--gray-10);

  &.ripe { background: var(--color-success-50); }
  &.half { background: var(--color-warning-50); }
  &.unripe { background: var(--color-info-50); }
}

.stat-label {
  color: var(--gray-600);
  font-size: 11px;
}

.stat-item strong {
  color: var(--gray-1000);
  font-size: 20px;
  font-weight: 700;
}

.ripe strong { color: var(--color-success-700); }
.half strong { color: var(--color-warning-900); }
.unripe strong { color: var(--color-info-700); }

/* 成熟度进度条 */
.maturity-bar {
  margin-top: 4px;
}

.bar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--gray-600);

  strong {
    font-size: 15px;
    color: var(--gray-1000);
    &.ready { color: var(--color-success-700); }
  }
}

.bar-track {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: var(--gray-150);
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--color-info-500);
  transition: width 0.5s ease;
  &.ready { background: var(--color-success-500); }
}

.bar-threshold {
  position: absolute;
  top: -3px;
  width: 2px;
  height: 14px;
  background: var(--color-error-500);
  border-radius: 1px;
}

.recommendation {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--main-50);
  color: var(--gray-800);
  font-size: 13px;
  line-height: 20px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--gray-400);

  p {
    margin: 0;
    font-size: 14px;
  }
}

/* 汇总卡片 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 90px;
  padding: 14px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
  color: var(--main-color);

  span {
    display: block;
    color: var(--gray-600);
    font-size: 12px;
  }

  strong {
    display: block;
    margin-top: 4px;
    color: var(--gray-1000);
    font-size: 22px;
    font-weight: 700;
  }

  p {
    margin: 4px 0 0;
    color: var(--gray-600);
    font-size: 12px;
  }
}

/* 历史记录 */
.records-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(300px, 0.75fr);
  gap: 16px;
}

.scan-panel, .advice-panel {
  padding: 18px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.scan-list, .advice-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.scan-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 100px 72px;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-10);
}

.scan-main strong {
  display: block;
  color: var(--gray-1000);
  font-size: 13px;
  font-weight: 650;
}

.scan-main span {
  display: block;
  color: var(--gray-500);
  font-size: 12px;
}

.scan-numbers {
  text-align: right;

  span {
    display: block;
    color: var(--gray-500);
    font-size: 11px;
  }

  strong {
    color: var(--gray-1000);
    font-size: 18px;
    font-weight: 700;
    &.ready { color: var(--color-success-700); }
  }
}

.scan-advice {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  background: var(--color-info-50);
  color: var(--color-info-700);
  font-size: 12px;
  font-weight: 600;
  &.ready {
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-10);
}

.advice-level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;

  &.ready {
    background: var(--color-success-50);
    color: var(--color-success-700);
  }
  &.watch {
    background: var(--color-warning-50);
    color: var(--color-warning-900);
  }
  &.normal {
    background: var(--color-info-50);
    color: var(--color-info-700);
  }
}

.advice-item strong {
  display: block;
  color: var(--gray-1000);
  font-size: 13px;
  font-weight: 650;
}

.advice-item p {
  margin: 4px 0 0;
  color: var(--gray-600);
  font-size: 12px;
}

.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  color: var(--gray-400);

  p {
    margin: 0;
    font-size: 14px;
  }
}

@media (max-width: 1180px) {
  .preview-result-section {
    grid-template-columns: 1fr;
  }
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .records-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .detect-action-bar {
    flex-direction: column;
    gap: 12px;
  }
  .action-left, .action-right {
    width: 100%;
    justify-content: center;
  }
  .summary-grid, .scan-row {
    grid-template-columns: 1fr;
  }
  .scan-numbers {
    text-align: left;
  }
}
</style>
