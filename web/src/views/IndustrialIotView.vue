<template>
  <div class="industrial-iot-view layout-container">
    <PageHeader title="智能温室物联网" :show-border="true">
      <template #info>
        <PageAgentDropdown default-agent="iot-controller" />
        <span class="header-status">
          <Activity :size="14" />
          在线监测
        </span>
      </template>
    </PageHeader>

    <main class="iot-content">
      <section class="overview-band">
        <div>
          <p class="eyebrow">环境与水培联动监控</p>
          <h2>空气、水培营养液与执行器状态</h2>
        </div>
        <div class="mode-panel">
          <div class="mode-item">
            <div>
              <span class="mode-title">自主模式</span>
              <span class="mode-desc">按预设阈值自动联动执行器</span>
            </div>
            <a-switch v-model:checked="autonomousMode" @change="toggleAutoMode" />
          </div>
          <div class="mode-item">
            <div>
              <span class="mode-title">AI 模式</span>
              <span class="mode-desc">启用智能策略辅助调控</span>
            </div>
            <a-switch v-model:checked="aiMode" @change="toggleAiMode" />
          </div>
        </div>
      </section>

      <div class="metrics-grid">
        <section class="monitor-section">
          <div class="section-heading">
            <Cloud :size="18" />
            <h3>空气环境</h3>
          </div>
          <div class="metric-list">
            <article v-for="metric in airMetrics" :key="metric.label" class="metric-card">
              <component :is="metric.icon" :size="20" class="metric-icon" />
              <div class="metric-body">
                <span class="metric-label">{{ metric.label }}</span>
                <strong>{{ metric.value }}</strong>
                <span class="metric-range">{{ metric.range }}</span>
              </div>
            </article>
          </div>
        </section>

        <section class="monitor-section">
          <div class="section-heading">
            <Droplets :size="18" />
            <h3>水培营养液</h3>
          </div>
          <div class="metric-list hydroponic-list">
            <article v-for="metric in hydroponicMetrics" :key="metric.label" class="metric-card">
              <component :is="metric.icon" :size="20" class="metric-icon" />
              <div class="metric-body">
                <span class="metric-label">{{ metric.label }}</span>
                <strong>{{ metric.value }}</strong>
                <span class="metric-range">{{ metric.range }}</span>
              </div>
            </article>
          </div>
        </section>
      </div>

      <section class="actuator-section">
        <div class="section-heading">
          <Cpu :size="18" />
          <h3>执行器控制台</h3>
        </div>
        <div class="actuator-grid">
          <article v-for="item in actuators" :key="item.key" class="actuator-row">
            <div class="actuator-info">
              <component :is="item.icon" :size="20" />
              <div>
                <span class="actuator-title">{{ item.name }}</span>
                <span class="actuator-desc">{{ item.desc }}</span>
              </div>
            </div>
            <a-switch
              v-model:checked="actuatorState[item.key]"
              @change="() => toggleActuator(item.key)"
            />
          </article>
        </div>
      </section>

      <!-- AI 控制建议（AI 模式开启时显示） -->
      <section v-if="aiMode" class="ai-panel">
        <div class="section-heading">
          <Bot :size="18" />
          <h3>AI 控制建议</h3>
          <span v-if="aiLoading" class="ai-badge loading">分析中...</span>
          <span v-else class="ai-badge">基于实时数据</span>
        </div>
        <div class="ai-content" v-html="renderAi(aiAnalysis)"></div>
        <button class="ai-refresh" :disabled="aiLoading" @click="runAiAnalysis">
          <RefreshCw :size="14" :class="{ spin: aiLoading }" /> 刷新分析
        </button>
      </section>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import MarkdownIt from 'markdown-it'
import {
  Activity,
  Bot,
  Cloud,
  Cpu,
  Droplets,
  RefreshCw,
  FlaskConical,
  Gauge,
  Leaf,
  Power,
  Sun,
  Thermometer,
  Waves,
  Wind
} from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import PageAgentDropdown from '@/components/PageAgentDropdown.vue'
import { fetchIotDashboard, setActuator, setMode } from '@/apis/iot_api'
import { message } from 'ant-design-vue'

// ---- 模式开关 ----
// 自主模式 ON  → 执行器锁死，只能看不能操作（设备端自动控制）
// 自主模式 OFF → 执行器解锁，用户可手动开关
const autonomousMode = ref(true)
const aiMode = ref(false)
const mqttConnected = ref(false)

// ---- 传感器数据（来自 API）----
const airData = ref(null)
const soilData = ref(null)

// ---- 执行器状态（来自 API）----
const actuatorState = ref({
  irrigation: false,
  mist: true,
  ventilation: false,
  pump: true
})

// ---- 轮询 ----
let pollTimer = null
const POLL_INTERVAL_MS = 5000

// ---- 从 API 数据计算展示指标 ----
const airMetrics = computed(() => {
  const a = airData.value
  return [
    { label: '二氧化碳浓度', value: a ? `${a.co2} ppm` : '--', range: '目标 500-900 ppm', icon: Gauge },
    { label: '光照强度', value: a ? `${a.illumination.toLocaleString()} lx` : '--', range: '目标 15,000-25,000 lx', icon: Sun },
    { label: '温度', value: a ? `${a.temp} °C` : '--', range: '目标 22-28 °C', icon: Thermometer },
    { label: '湿度', value: a ? `${a.humidity}%` : '--', range: '目标 60-75%', icon: Droplets }
  ]
})

const hydroponicMetrics = computed(() => {
  const s = soilData.value
  return [
    { label: '氮', value: s ? `${s.nitrogen} mg/L` : '--', range: '营养元素 N', icon: Leaf },
    { label: '磷', value: s ? `${s.phosphorus} mg/L` : '--', range: '营养元素 P', icon: Leaf },
    { label: '钾', value: s ? `${s.potassium} mg/L` : '--', range: '营养元素 K', icon: Leaf },
    { label: 'pH 值', value: s ? `${s.ph_value}` : '--', range: '目标 5.8-6.5', icon: FlaskConical },
    { label: 'EC 值', value: s ? `${(s.soil_conductivity / 1000).toFixed(1)} mS/cm` : '--', range: '目标 1.4-2.2 mS/cm', icon: Gauge },
    { label: '水温', value: s ? `${s.soil_temperature} °C` : '--', range: '目标 20-24 °C', icon: Thermometer }
  ]
})

const actuators = [
  { key: 'mist', name: '水雾培开关', desc: '控制雾化供液与根区湿润', icon: Waves },
  { key: 'ventilation', name: '通风开关', desc: '控制风机换气与温湿度平衡', icon: Wind },
  { key: 'pump', name: '水泵开关', desc: '控制营养液循环供给', icon: Power }
]

// ---- 数据获取 ----
async function loadDashboard() {
  try {
    const data = await fetchIotDashboard()
    mqttConnected.value = true
    if (data.air) airData.value = data.air
    if (data.soil) soilData.value = data.soil
    if (data.actuators) {
      const a = data.actuators
      actuatorState.value.irrigation = a.irrigation
      actuatorState.value.mist = a.mist
      actuatorState.value.ventilation = a.ventilation
      actuatorState.value.pump = a.pump
      autonomousMode.value = a.auto_mode
      aiMode.value = a.ai_mode
    }
  } catch (e) {
    if (e.response?.status === 404) {
      mqttConnected.value = true
    } else {
      mqttConnected.value = false
      console.warn('IoT dashboard fetch failed:', e)
    }
  }
}

// ---- 执行器控制 ----
// 逻辑：v-model 先更新 UI（乐观更新），toggleActuator 发 API，
// 成功 → 保持新值；失败 → 回滚到旧值
const pendingKeys = new Set()
async function toggleActuator(key) {
  if (pendingKeys.has(key)) return
  pendingKeys.add(key)
  const newValue = actuatorState.value[key]   // v-model 已经设好新值
  const oldValue = !newValue
  try {
    await setActuator(key, newValue)
  } catch {
    actuatorState.value[key] = oldValue
    message.error('指令发送失败，请检查 MQTT 连接')
  } finally {
    pendingKeys.delete(key)
  }
}

// ---- 模式控制（互斥）----
async function toggleAutoMode(val) {
  if (!val) return  // 不允许直接关，只能通过开另一个来切换
  const oldAi = aiMode.value
  aiMode.value = false
  try {
    await setMode('auto')
  } catch {
    autonomousMode.value = false
    aiMode.value = oldAi
    message.error('模式切换失败，请检查 MQTT 连接')
  }
}
async function toggleAiMode(val) {
  if (!val) {
    if (aiTimer) { clearInterval(aiTimer); aiTimer = null }
    aiAnalysis.value = ''
    return
  }
  const oldAuto = autonomousMode.value
  autonomousMode.value = false
  try {
    await setMode('ai')
    await loadDashboard()
    await runAiAnalysis()
    startAiLoop()
  } catch {
    aiMode.value = false
    autonomousMode.value = oldAuto
    if (aiTimer) { clearInterval(aiTimer); aiTimer = null }
    message.error('模式切换失败，请检查 MQTT 连接')
  }
}

// AI 控制 —— 直接让 Agent 决策并执行
const aiAnalysis = ref('')
const aiLoading = ref(false)
const aiThreadId = ref(null)
const md = new MarkdownIt({ breaks: true })

async function runAiAnalysis() {
  if (!aiMode.value) return
  aiLoading.value = true
  aiAnalysis.value = '🔍 AI 正在读取传感器数据...'
  try {
    const { agentApi, threadApi } = await import('@/apis/agent_api')
    const { useAgentStore } = await import('@/stores/agent')
    const agentStore = useAgentStore()
    if (!agentStore.isInitialized) await agentStore.initialize()

    // 确保使用温室总管
    const master = agentStore.agents.find(a => a.slug === 'greenhouse-master' || a.id === 'greenhouse-master')
    if (master && agentStore.selectedAgentId !== master.id) await agentStore.selectAgent(master.id)
    const agentId = agentStore.selectedAgentId

    // 创建线程
    if (!aiThreadId.value) {
      const tr = await threadApi.createThread(agentId, 'AI自动控制')
      aiThreadId.value = tr?.id || tr?.thread_id
    }

    const a = airData.value; const s = soilData.value
    const query = `温室实时数据：温度${a?.temp || '?'}°C，湿度${a?.humidity || '?'}%，CO2 ${a?.co2 || '?'}ppm，光照${a?.illumination || '?'}lx，pH ${s?.ph_value || '?'}，EC ${s ? (s.soil_conductivity/1000).toFixed(1) : '?'}mS/cm。适宜：22-28°C/60-75%/500-900ppm/5.8-6.5/1.4-2.2。
直接用 control_actuator 调整异常设备（无需确认），调整后一句话报告结果。格式：每行一个操作，如「已开通风：温度28.5偏高」`

    aiAnalysis.value = '⚙️ AI 正在分析和执行...'
    const runRes = await agentApi.createAgentRun({ query, agent_id: agentId, thread_id: aiThreadId.value, meta: {} })
    const runId = runRes?.run_id
    if (!runId) throw new Error('Agent 启动失败')

    // 等待 SSE 完成
    const resp = await agentApi.streamAgentRunEvents(runId, '0-0')
    const reader = resp.body.getReader(); const dec = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read(); if (done) break
      buf += dec.decode(value, { stream: true }); buf.split('\n')
    }

    // 拉取最终结果
    await new Promise(r => setTimeout(r, 1500))
    const hist = await agentApi.getAgentHistory(aiThreadId.value)
    const all = hist?.history || hist?.messages || hist?.data || []
    let result = ''
    for (let i = all.length - 1; i >= 0; i--) {
      if ((all[i].type === 'ai' || all[i].role === 'assistant') && all[i].content?.trim()) {
        result = all[i].content.trim(); break
      }
    }
    aiAnalysis.value = result || 'AI 已完成控制操作（详情请查看执行器状态）'

    // 刷新仪表盘数据
    await loadDashboard()
  } catch (e) {
    aiAnalysis.value = 'AI 控制失败：' + (e.message || '未知')
  } finally {
    aiLoading.value = false
  }
}

// AI 模式定时巡检（每 60 秒）
let aiTimer = null
async function startAiLoop() {
  if (aiTimer) clearInterval(aiTimer)
  if (!aiMode.value) return
  aiTimer = setInterval(async () => {
    await loadDashboard()
    if (aiMode.value) await runAiAnalysis()
  }, 60000)
}

function renderAi(text) { return text ? md.render(text) : '' }

onMounted(() => {
  loadDashboard()
  pollTimer = setInterval(loadDashboard, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  clearInterval(pollTimer)
  if (aiTimer) clearInterval(aiTimer)
})
</script>

<style scoped lang="less">
.industrial-iot-view {
  min-height: 100%;
  background: var(--gray-25);
}

.header-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  background: var(--color-success-50);
  color: var(--color-success-700);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

.iot-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--page-padding);
}

.overview-band,
.monitor-section,
.actuator-section {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.overview-band {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 520px);
  align-items: center;
  gap: 20px;
  padding: 20px 24px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--main-color);
  font-size: 12px;
  font-weight: 650;
}

.overview-band h2 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 22px;
  font-weight: 650;
  line-height: 1.35;
}

.mode-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.mode-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.mode-title,
.mode-desc,
.metric-label,
.metric-range,
.actuator-title,
.actuator-desc {
  display: block;
}

.mode-title,
.actuator-title {
  color: var(--gray-1000);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.mode-desc,
.metric-range,
.actuator-desc {
  margin-top: 2px;
  color: var(--gray-600);
  font-size: 12px;
  line-height: 18px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr);
  gap: 16px;
}

.monitor-section,
.actuator-section {
  padding: 18px;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: var(--main-color);
}

.section-heading h3 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 16px;
  font-weight: 650;
  line-height: 22px;
}

.metric-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.hydroponic-list {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 104px;
  padding: 14px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.metric-icon {
  flex: 0 0 auto;
  color: var(--main-color);
}

.metric-body {
  min-width: 0;
}

.metric-label {
  color: var(--gray-600);
  font-size: 13px;
  line-height: 18px;
}

.metric-body strong {
  display: block;
  margin-top: 8px;
  color: var(--gray-1000);
  font-size: 24px;
  font-weight: 700;
  line-height: 30px;
  white-space: nowrap;
}

.actuator-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.actuator-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 82px;
  padding: 14px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.actuator-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: var(--main-color);
}

@media (max-width: 1180px) {
  .overview-band,
  .metrics-grid,
  .actuator-grid {
    grid-template-columns: 1fr;
  }

  .hydroponic-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .overview-band {
    padding: 16px;
  }

  .mode-panel,
  .metric-list,
  .hydroponic-list {
    grid-template-columns: 1fr;
  }

  .metric-body strong {
    font-size: 22px;
  }
}
</style>
