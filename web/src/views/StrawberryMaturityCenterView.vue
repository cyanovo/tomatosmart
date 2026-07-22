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
        <span class="status-pill">
          <ScanLine :size="14" />
          循迹小车在线
        </span>
      </template>
    </PageHeader>

    <main class="maturity-content">
      <section class="hero-panel">
        <img
          src="/images/Strawberry/strawberry-harvest-quality.png"
          alt="草莓采收与分级"
          class="hero-image"
        />
        <div class="hero-copy">
          <p>最新扫描 · {{ latestScan.time }}</p>
          <h2>{{ latestZoneName }}成熟度 {{ latestScan.maturity }}%，{{ latestScan.maturity >= harvestThreshold ? '建议执行采摘小车' : '建议继续观察' }}</h2>
          <span>本次识别草莓 {{ latestScan.count.toLocaleString() }} 颗，其中成熟果 {{ matureCount.toLocaleString() }} 颗，优先采摘 {{ latestScan.path }}。</span>
        </div>
        <button class="harvest-action" type="button" @click="goHarvestDispatch">
          <Truck :size="18" />
          执行采摘小车
        </button>
      </section>

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

      <section class="records-layout">
        <article class="scan-panel">
          <div class="section-title">
            <Route :size="18" />
            <h3>循迹扫描记录</h3>
          </div>
          <div class="scan-list">
            <div v-for="scan in scans" :key="scan.id" class="scan-row">
              <div class="scan-main">
                <strong>{{ scan.zoneName }} · {{ scan.path }}</strong>
                <span>{{ scan.time }} · 小车 {{ scan.robot }}</span>
              </div>
              <div class="scan-numbers">
                <span>{{ scan.count }} 颗</span>
                <strong :class="{ ready: scan.maturity >= harvestThreshold }">{{ scan.maturity }}%</strong>
              </div>
              <span class="scan-advice" :class="{ ready: scan.maturity >= harvestThreshold }">
                {{ scan.maturity >= harvestThreshold ? '可采摘' : '继续观察' }}
              </span>
            </div>
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
import { computed, ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ClipboardCheck,
  Gauge,
  Route,
  ScanLine,
  Sprout,
  Timer,
  Truck
} from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import PageAgentDropdown from '@/components/PageAgentDropdown.vue'
import { scanRecords, zoneConfig, getHarvestThreshold, setHarvestThreshold } from '@/data/strawberryData.js'

const router = useRouter()

// 可配置采摘阈值
const harvestThreshold = ref(getHarvestThreshold())
function persistThreshold() {
  const n = harvestThreshold.value
  if (n >= 0 && n <= 100) {
    setHarvestThreshold(n)
  }
}

// 最新扫描（取今天最近的一条）
const latestScan = computed(() => {
  const today = scanRecords.filter(s => s.time.startsWith('今天'))
  return today.length ? today.reduce((a, b) => (a.time > b.time ? a : b)) : scanRecords[0]
})

const latestZoneName = computed(() => zoneConfig[latestScan.value.zone]?.name || '')
const matureCount = computed(() => Math.round(latestScan.value.count * latestScan.value.maturity / 100))
const yieldKg = computed(() => Math.round(matureCount.value * 0.1))
const prevScan = computed(() => scanRecords.find(s => s.zone === latestScan.value.zone && s.time.startsWith('昨天')))

const summary = computed(() => [
  {
    label: '本次识别总数',
    value: `${latestScan.value.count.toLocaleString()} 颗`,
    note: prevScan.value ? `较上次 ${latestScan.value.count > prevScan.value.count ? '+' : ''}${latestScan.value.count - prevScan.value.count} 颗` : '暂无对比',
    icon: Sprout
  },
  {
    label: '平均成熟度',
    value: `${latestScan.value.maturity}%`,
    note: latestScan.value.maturity >= harvestThreshold.value ? '达到采摘阈值' : '未达阈值',
    icon: Gauge
  },
  {
    label: '建议采摘量',
    value: `${yieldKg.value} kg`,
    note: `${latestScan.value.path} 优先`,
    icon: Truck
  },
  {
    label: '扫描耗时',
    value: '18 分钟',
    note: `路径 ${latestScan.value.id} 完成`,
    icon: Timer
  }
])

// scanRecords 映射 zone id → 显示名
const scans = computed(() =>
  scanRecords.map(s => ({
    ...s,
    zoneName: zoneConfig[s.zone]?.name || s.zone
  }))
)

// 基础判断逻辑（同步），AI 生成描述文字（异步）
const harvestAdvice = ref([])
const adviceLoading = ref(false)

// 同步计算的兜底建议（AI 加载前显示）
const fallbackAdvice = computed(() => {
  const t = harvestThreshold.value
  const items = []
  const zoneToday = scanRecords.filter(s => s.time.includes('今天'))
  for (const s of zoneToday) {
    const zn = zoneConfig[s.zone]?.name || s.zone
    if (s.maturity >= t) items.push({ level: 'ready', levelText: '执行', title: `${zn} 成熟度 ${s.maturity}%`, desc: '已达采摘阈值，建议立即派发采摘小车。' })
    else if (s.maturity >= t - 10) items.push({ level: 'watch', levelText: '观察', title: `${zn} 接近采摘窗口`, desc: `成熟度 ${s.maturity}%，建议安排复扫。` })
    else items.push({ level: 'normal', levelText: '正常', title: `${zn} 未达采摘阈值`, desc: '继续观察，维持当前策略。' })
  }
  return items
})

// 页面实际显示的（AI 加载中用兜底）
const displayAdvice = computed(() => {
  if (harvestAdvice.value.length) return harvestAdvice.value
  return fallbackAdvice.value
})

function buildAdviceItems(t, scans) {
  const items = []
  const latestZone = latestScan.value.zone
  const zoneToday = scans.filter(s => s.zone === latestZone && s.time.includes('今天'))
  const topMaturity = zoneToday.length ? Math.max(...zoneToday.map(s => s.maturity)) : 0
  if (topMaturity >= t) {
    items.push({ zone: latestZone, maturity: topMaturity, status: 'ready', threshold: t })
  } else {
    items.push({ zone: latestZone, maturity: topMaturity, status: 'watch', threshold: t })
  }
  const otherScans = scans.filter(s => s.zone !== latestZone && s.time.includes('今天'))
  for (const s of otherScans) {
    if (s.maturity >= t) items.push({ zone: s.zone, maturity: s.maturity, status: 'ready', threshold: t })
    else if (s.maturity >= t - 10) items.push({ zone: s.zone, maturity: s.maturity, status: 'watch', threshold: t })
    else items.push({ zone: s.zone, maturity: s.maturity, status: 'normal', threshold: t })
  }
  return items
}

const baseAdviceItems = computed(() => buildAdviceItems(harvestThreshold.value, scanRecords))

async function loadHarvestAdvice() {
  const items = baseAdviceItems.value
  if (!items.length) { harvestAdvice.value = []; return }
  adviceLoading.value = true
  try {
    // 构造扫描数据摘要
    let scanText = '草莓温室成熟度扫描数据：\n'
    for (const item of items) {
      const zn = zoneConfig[item.zone]?.name || item.zone
      const statusText = item.status === 'ready' ? '已达采摘阈值' : (item.status === 'watch' ? '接近阈值' : '未达阈值')
      scanText += `${zn}：成熟度 ${item.maturity}%，${statusText}（阈值 ${item.threshold}%）\n`
    }
    scanText += `\n列表空间有限！为每个区域一行：A区：标题≤8字，描述≤40字。已达阈值写"立即采摘"，接近写"安排复扫"，未达写"继续观察"。`

    // 通过 Agent run + SSE 流式获取回复
    const { agentApi, threadApi } = await import('@/apis/agent_api')
    const { useAgentStore } = await import('@/stores/agent')
    const agentStore = useAgentStore()
    if (!agentStore.isInitialized) await agentStore.initialize()
    const master = agentStore.agents.find(a => a.slug === 'greenhouse-master' || a.id === 'greenhouse-master')
    const agentId = master?.id || agentStore.selectedAgentId
    if (!agentId) throw new Error('无可用智能体')

    const tr = await threadApi.createThread(agentId, '采收建议')
    const tid = tr?.id || tr?.thread_id
    const runRes = await agentApi.createAgentRun({ query: scanText, agent_id: agentId, thread_id: tid, meta: {} })
    const runId = runRes?.run_id
    if (!runId) throw new Error('创建运行失败')

    // SSE 流式读取
    const resp = await agentApi.streamAgentRunEvents(runId, '0-0')
    const reader = resp.body.getReader(); const dec = new TextDecoder()
    let buf = ''; let text = ''
    while (true) {
      const { done, value } = await reader.read(); if (done) break
      buf += dec.decode(value, { stream: true }); const lines = buf.split('\n'); buf = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        try {
          const env = JSON.parse(line.slice(5).trim())
          if (!env?.payload) continue
          const its = env.payload.items || (env.payload.chunk ? [env.payload.chunk] : [])
          for (const item of its) {
            const t = (typeof item.content === 'string') ? item.content : (Array.isArray(item.content) ? item.content.map(c => typeof c === 'string' ? c : c?.text || '').join('') : '')
            if (t) text += t
          }
        } catch {}
      }
    }

    // 从历史拉取完整回复
    await new Promise(r => setTimeout(r, 1000))
    try {
      const hist = await agentApi.getAgentHistory(tid)
      const all = hist?.history || hist?.messages || hist?.data || []
      for (let i = all.length - 1; i >= 0; i--) {
        if ((all[i].type === 'ai' || all[i].role === 'assistant') && all[i].content?.trim()) {
          text = all[i].content.trim(); break
        }
      }
    } catch {}
    if (!text) { harvestAdvice.value = items.map(i => _fallbackAdvice(i)); return }

    // 解析 AI 回复，匹配到各区域
    const result = []
    const lines = text.split('\n').filter(l => l.trim())
    for (const item of items) {
      const zn = zoneConfig[item.zone]?.name || item.zone
      const matched = lines.find(l => l.includes(zn))
      const desc = matched ? matched.replace(/^[\d\.\-\*\s]+/, '').trim().slice(0, 100) : ''
      const levelMap = { ready: 'ready', watch: 'watch', normal: 'normal' }
      const textMap = { ready: '执行', watch: '观察', normal: '正常' }
      result.push({
        level: levelMap[item.status], levelText: textMap[item.status],
        title: `${zn} 成熟度 ${item.maturity}%` + (item.status === 'ready' ? ' 已达阈值' : ''),
        desc: desc || _fallbackAdvice(item).desc
      })
    }
    harvestAdvice.value = result
  } catch {
    harvestAdvice.value = items.map(i => _fallbackAdvice(i))
  } finally {
    adviceLoading.value = false
  }
}

function _fallbackAdvice(item) {
  const zn = zoneConfig[item.zone]?.name || item.zone
  if (item.status === 'ready') return { level: 'ready', levelText: '执行', title: `${zn} 达采摘阈值`, desc: '建议立即派发采摘小车。' }
  if (item.status === 'watch') return { level: 'watch', levelText: '观察', title: `${zn} 接近采摘窗口`, desc: '建议安排复扫。' }
  return { level: 'normal', levelText: '正常', title: `${zn} 暂未达阈值`, desc: '继续观察，维持当前策略。' }
}

function goHarvestDispatch() {
  router.push(`/strawberry-harvest-dispatch?zone=${latestScan.value.zone}`)
}

onMounted(() => { loadHarvestAdvice() })
watch(harvestThreshold, () => { loadHarvestAdvice() })
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
  background: var(--color-success-50);
  color: var(--color-success-700);
  font-size: 12px;
  font-weight: 600;
}

.maturity-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--page-padding);
}

.hero-panel,
.summary-card,
.scan-panel,
.advice-panel {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 520px) auto;
  align-items: center;
  overflow: hidden;
}

.hero-image {
  width: 100%;
  height: 260px;
  object-fit: cover;
}

.hero-copy {
  padding: 24px;
}

.hero-copy p {
  margin: 0 0 8px;
  color: var(--main-color);
  font-size: 12px;
  font-weight: 700;
}

.hero-copy h2 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.35;
}

.hero-copy span {
  display: block;
  margin-top: 10px;
  color: var(--gray-600);
  font-size: 14px;
  line-height: 22px;
}

.harvest-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 150px;
  height: 40px;
  margin-right: 24px;
  border: 1px solid var(--main-color);
  border-radius: 8px;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
}

.harvest-action:disabled {
  border-color: var(--gray-200);
  background: var(--gray-100);
  color: var(--gray-500);
  cursor: not-allowed;
}

.threshold-config {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--gray-600);
}

.threshold-input {
  width: 40px;
  height: 22px;
  padding: 0 4px;
  border: 1px solid var(--gray-200);
  border-radius: 4px;
  background: var(--gray-0);
  color: var(--gray-1000);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
  outline: none;

  &:focus { border-color: var(--main-color); }
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 108px;
  padding: 14px;
  color: var(--main-color);
}

.summary-card span,
.scan-main span {
  display: block;
  color: var(--gray-600);
  font-size: 12px;
}

.summary-card strong {
  display: block;
  margin-top: 6px;
  color: var(--gray-1000);
  font-size: 24px;
  font-weight: 700;
}

.summary-card p,
.advice-item p {
  margin: 4px 0 0;
  color: var(--gray-600);
  font-size: 12px;
  line-height: 18px;
}

.records-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(340px, 0.75fr);
  gap: 16px;
}

.scan-panel,
.advice-panel {
  padding: 18px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: var(--main-color);
}

.section-title h3 {
  margin: 0;
  color: var(--gray-1000);
  font-size: 16px;
  font-weight: 650;
}

.scan-list,
.advice-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.scan-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 110px 72px;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

.scan-main strong,
.advice-item strong {
  display: block;
  color: var(--gray-1000);
  font-size: 14px;
  font-weight: 650;
}

.scan-numbers {
  text-align: right;
}

.scan-numbers span {
  display: block;
  color: var(--gray-600);
  font-size: 12px;
}

.scan-numbers strong {
  color: var(--gray-1000);
  font-size: 20px;
  font-weight: 700;
}

.scan-numbers strong.ready {
  color: var(--color-success-700);
}

.scan-advice,
.advice-level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  background: var(--color-info-50);
  color: var(--color-info-700);
  font-size: 12px;
  font-weight: 650;
}

.scan-advice.ready,
.advice-level.ready {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.advice-level.watch {
  background: var(--color-warning-50);
  color: var(--color-warning-900);
}

.advice-level.normal {
  background: var(--color-info-50);
  color: var(--color-info-700);
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-10);
}

@media (max-width: 1180px) {
  .hero-panel,
  .records-layout,
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .harvest-action {
    margin: 0 24px 24px;
  }
}

@media (max-width: 760px) {
  .hero-panel,
  .records-layout,
  .summary-grid,
  .scan-row {
    grid-template-columns: 1fr;
  }

  .scan-numbers {
    text-align: left;
  }
}

</style>
