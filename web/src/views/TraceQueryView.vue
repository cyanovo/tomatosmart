<template>
  <div class="tc-page">
    <!-- Hero 区域 -->
    <header class="tc-hero">
      <div class="tc-hero-bg">
        <div class="tc-hero-grain"></div>
      </div>
      <div class="tc-hero-content">
        <div class="tc-hero-icon">
          <Fingerprint :size="28" />
        </div>
        <h1 class="tc-hero-title">番茄溯源</h1>
        <p class="tc-hero-slogan">从田间到餐桌，每一颗番茄都有迹可循</p>
        <p class="tc-hero-sub">扫码或输入溯源码，即刻查看种植、采摘、质检全链路信息</p>
      </div>
    </header>

    <!-- 查询区 -->
    <main class="tc-main">
      <div class="tc-search-card">
        <div class="tc-search-inner">
          <input
            v-model="queryCode"
            class="tc-search-input"
            placeholder="输入溯源码或批次编号"
            @keyup.enter="handleQuery"
          />
          <div class="tc-search-actions">
            <button class="tc-btn-scan" @click="toggleScanner" :class="{ active: showScanner }">
              <ScanLine :size="16" />
              <span>{{ showScanner ? '关闭' : '扫码' }}</span>
            </button>
            <button class="tc-btn-query" @click="handleQuery" :disabled="!queryCode.trim() || loading">
              <Search :size="16" />
              <span>查询</span>
            </button>
          </div>
        </div>
        <!-- 扫码器 -->
        <Transition name="slide-down">
          <div v-if="showScanner" class="tc-scanner-wrap">
            <div id="qr-reader" class="tc-scanner"></div>
            <p class="tc-scanner-hint">将包装上的二维码对准摄像头</p>
          </div>
        </Transition>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="tc-loading">
        <div class="tc-spinner"></div>
        <span>溯源信息查询中...</span>
      </div>

      <!-- 错误 -->
      <Transition name="fade">
        <div v-if="error" class="tc-error-card">
          <AlertCircle :size="18" />
          <span>{{ error }}</span>
        </div>
      </Transition>

      <!-- ═══ 溯源报告 ═══ -->
      <Transition name="fade-up">
        <div v-if="report" class="tc-report">
          <!-- 校验状态横幅 -->
          <div class="tc-trust-bar" :class="{ ok: isVerified, fail: report.tamper_detected }">
            <div class="tc-trust-icon">
              <ShieldCheck v-if="isVerified" :size="20" />
              <ShieldAlert v-else :size="20" />
            </div>
            <div class="tc-trust-text">
              <strong>{{ isVerified ? '数据校验通过' : '数据校验异常' }}</strong>
              <span>{{ isVerified ? '溯源信息完整可信' : '检测到数据可能被篡改' }}</span>
            </div>
          </div>

          <!-- 旅程时间线 -->
          <div class="tc-timeline">
            <div class="tc-tl-step" :class="{ active: report.plant_date }">
              <div class="tc-tl-dot"><Sprout :size="14" /></div>
              <span>播种</span>
              <small v-if="report.plant_date">{{ report.plant_date }}</small>
            </div>
            <div class="tc-tl-line"></div>
            <div class="tc-tl-step" :class="{ active: report.harvest_date }">
              <div class="tc-tl-dot"><Package :size="14" /></div>
              <span>采摘</span>
              <small v-if="report.harvest_date">{{ report.harvest_date }}</small>
            </div>
            <div class="tc-tl-line"></div>
            <div class="tc-tl-step" :class="{ active: hasInspection }">
              <div class="tc-tl-dot"><ClipboardCheck :size="14" /></div>
              <span>质检</span>
              <small v-if="hasInspection">{{ report.inspections[0].result }}</small>
            </div>
            <div class="tc-tl-line"></div>
            <div class="tc-tl-step" :class="{ active: report.package_info }">
              <div class="tc-tl-dot"><Box :size="14" /></div>
              <span>包装</span>
              <small v-if="report.package_info">{{ report.package_info.package_date }}</small>
            </div>
          </div>

          <!-- 种植信息 -->
          <section class="tc-card">
            <div class="tc-card-header">
              <div class="tc-card-icon tc-icon-green"><Sprout :size="18" /></div>
              <h3>种植信息</h3>
            </div>
            <div class="tc-card-body">
              <div class="tc-row">
                <span class="tc-row-label">品种</span>
                <span class="tc-row-value tc-value-highlight">{{ report.seed_variety || '-' }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">地块</span>
                <span class="tc-row-value">{{ report.plot_name || '-' }} · {{ report.plot_location || '' }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">种子供应商</span>
                <span class="tc-row-value">{{ report.seed_supplier || '-' }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">种植日期</span>
                <span class="tc-row-value">{{ report.plant_date || '-' }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">批次编号</span>
                <span class="tc-row-value tc-value-mono">{{ report.batch_code }}</span>
              </div>
            </div>
          </section>

          <!-- 采摘信息 -->
          <section v-if="report.harvest_date" class="tc-card">
            <div class="tc-card-header">
              <div class="tc-card-icon tc-icon-orange"><Package :size="18" /></div>
              <h3>采摘信息</h3>
            </div>
            <div class="tc-card-body">
              <div class="tc-row">
                <span class="tc-row-label">采摘日期</span>
                <span class="tc-row-value">{{ report.harvest_date }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">产量</span>
                <span class="tc-row-value tc-value-highlight">{{ report.harvest_yield_kg ? report.harvest_yield_kg + ' kg' : '-' }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">等级</span>
                <span class="tc-row-value">
                  <span v-if="report.harvest_grade" class="tc-grade-badge">{{ report.harvest_grade }}</span>
                  <span v-else>-</span>
                </span>
              </div>
            </div>
          </section>

          <!-- 质检报告 -->
          <section v-if="hasInspection" class="tc-card">
            <div class="tc-card-header">
              <div class="tc-card-icon tc-icon-blue"><ClipboardCheck :size="18" /></div>
              <h3>质检报告</h3>
            </div>
            <div class="tc-card-body">
              <div v-for="(insp, i) in report.inspections" :key="i" class="tc-insp-row">
                <span class="tc-insp-type">{{ insp.type || insp.inspection_type }}</span>
                <span class="tc-insp-badge" :class="{ pass: insp.result === '合格' }">{{ insp.result }}</span>
                <span v-if="insp.lab" class="tc-insp-lab">{{ insp.lab }}</span>
              </div>
            </div>
          </section>

          <!-- 包装信息 -->
          <section v-if="report.package_info" class="tc-card">
            <div class="tc-card-header">
              <div class="tc-card-icon tc-icon-purple"><Box :size="18" /></div>
              <h3>包装信息</h3>
            </div>
            <div class="tc-card-body">
              <div class="tc-row">
                <span class="tc-row-label">包装日期</span>
                <span class="tc-row-value">{{ report.package_info.package_date || '-' }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">重量</span>
                <span class="tc-row-value">{{ report.package_info.weight_kg ? report.package_info.weight_kg + ' kg' : '-' }}</span>
              </div>
              <div class="tc-row">
                <span class="tc-row-label">生产批号</span>
                <span class="tc-row-value tc-value-mono">{{ report.package_info.lot_number || '-' }}</span>
              </div>
              <div v-if="report.package_info.package_spec" class="tc-row">
                <span class="tc-row-label">规格</span>
                <span class="tc-row-value">{{ report.package_info.package_spec }}</span>
              </div>
            </div>
          </section>

          <!-- 田间管理 -->
          <section v-if="hasActivities" class="tc-card">
            <div class="tc-card-header">
              <div class="tc-card-icon tc-icon-green"><Leaf :size="18" /></div>
              <h3>田间管理</h3>
            </div>
            <div class="tc-card-body tc-activity-list">
              <div v-for="(act, i) in report.activities_detail" :key="i" class="tc-act-item">
                <div class="tc-act-dot"></div>
                <div class="tc-act-content">
                  <div class="tc-act-head">
                    <span class="tc-act-type">{{ act.type }}</span>
                    <span class="tc-act-date">{{ act.datetime }}</span>
                  </div>
                  <p v-if="act.detail" class="tc-act-detail">{{ act.detail }}</p>
                  <p v-if="act.materials" class="tc-act-materials">物料：{{ act.materials }}</p>
                </div>
              </div>
            </div>
          </section>

          <!-- 照片 -->
          <section v-if="hasPhotos" class="tc-card">
            <div class="tc-card-header">
              <div class="tc-card-icon tc-icon-orange"><Camera :size="18" /></div>
              <h3>生长记录</h3>
            </div>
            <div class="tc-card-body">
              <div class="tc-photo-grid">
                <div v-for="(photo, i) in report.growth_photos" :key="'g'+i" class="tc-photo-item">
                  <img :src="photo.file_path" alt="生长照片" />
                  <span class="tc-photo-tag">生长</span>
                </div>
                <div v-for="(photo, i) in report.harvest_photos" :key="'h'+i" class="tc-photo-item">
                  <img :src="photo.file_path" alt="采摘照片" />
                  <span class="tc-photo-tag">采摘</span>
                </div>
              </div>
            </div>
          </section>

          <!-- 数据校验详情 -->
          <section class="tc-card tc-card-verify">
            <div class="tc-card-header">
              <div class="tc-card-icon tc-icon-blue"><ShieldCheck :size="18" /></div>
              <h3>数据校验</h3>
            </div>
            <div class="tc-card-body">
              <div class="tc-verify-item">
                <span>区块链验证</span>
                <span class="tc-verify-tag" :class="{ ok: report.blockchain_verified }">
                  {{ report.blockchain_verified ? '已上链' : '未上链' }}
                </span>
              </div>
              <div class="tc-verify-item">
                <span>数据完整性</span>
                <span class="tc-verify-tag" :class="{ ok: report.hash_verified, fail: !report.hash_verified }">
                  {{ report.hash_verified ? '完整' : '异常' }}
                </span>
              </div>
            </div>
          </section>

          <!-- 底部标语 -->
          <div class="tc-footer">
            <p>智能温室 · 区块链溯源 · 安心每一口</p>
          </div>
        </div>
      </Transition>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, nextTick } from 'vue'
import {
  Fingerprint, Search, ScanLine, AlertCircle, ShieldCheck, ShieldAlert,
  Sprout, Package, ClipboardCheck, Box, Camera, Leaf
} from 'lucide-vue-next'
import { traceQueryPublic, traceByBatchCodePublic } from '@/apis/trace_api'

const queryCode = ref('')
const report = ref(null)
const loading = ref(false)
const error = ref('')
const showScanner = ref(false)
let html5QrScanner = null

const isVerified = computed(() =>
  report.value && report.value.hash_verified && !report.value.tamper_detected
)
const hasInspection = computed(() =>
  report.value?.inspections?.length > 0
)
const hasActivities = computed(() =>
  report.value?.activities_detail?.length > 0
)
const hasPhotos = computed(() =>
  (report.value?.growth_photos?.length > 0) || (report.value?.harvest_photos?.length > 0)
)

async function handleQuery() {
  const code = queryCode.value.trim()
  if (!code) return
  loading.value = true
  error.value = ''
  report.value = null

  try {
    let res
    if (code.startsWith('TM')) {
      res = await traceQueryPublic(code)
    } else {
      res = await traceByBatchCodePublic(code)
    }
    if (res.ok) {
      report.value = res.report
    } else {
      error.value = res.detail || '查询失败'
    }
  } catch (e) {
    error.value = e.message || '溯源码无效或已失效'
  } finally {
    loading.value = false
  }
}

async function toggleScanner() {
  if (showScanner.value) {
    stopScanner()
    return
  }
  showScanner.value = true
  await nextTick()
  startScanner()
}

function startScanner() {
  import('html5-qrcode').then(({ Html5Qrcode }) => {
    html5QrScanner = new Html5Qrcode('qr-reader')
    html5QrScanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        queryCode.value = decodedText
        stopScanner()
        handleQuery()
      },
      () => {}
    ).catch(() => {
      error.value = '无法访问摄像头，请检查浏览器权限设置'
      showScanner.value = false
    })
  })
}

function stopScanner() {
  if (html5QrScanner) {
    html5QrScanner.stop().then(() => {
      html5QrScanner.clear()
      html5QrScanner = null
    }).catch(() => {})
  }
  showScanner.value = false
}

onBeforeUnmount(() => {
  stopScanner()
})
</script>

<style lang="less" scoped>
.tc-page {
  min-height: 100vh;
  background: #f7f5f3;
}

// ═══════════════════════════════════════════════
//  Hero 区域
// ═══════════════════════════════════════════════
.tc-hero {
  position: relative;
  padding: 48px 20px 40px;
  text-align: center;
  overflow: hidden;
}
.tc-hero-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--main-700) 0%, var(--main-600) 50%, #b44a4c 100%);
  z-index: 0;
}
.tc-hero-grain {
  position: absolute;
  inset: 0;
  opacity: .06;
  background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.tc-hero-content {
  position: relative;
  z-index: 1;
  max-width: 520px;
  margin: 0 auto;
}
.tc-hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(255,255,255,.15);
  backdrop-filter: blur(8px);
  color: #fff;
  margin-bottom: 16px;
}
.tc-hero-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px;
  letter-spacing: 2px;
}
.tc-hero-slogan {
  font-size: 16px;
  color: rgba(255,255,255,.9);
  margin: 0 0 6px;
  font-weight: 500;
}
.tc-hero-sub {
  font-size: 13px;
  color: rgba(255,255,255,.6);
  margin: 0;
}

// ═══════════════════════════════════════════════
//  主体
// ═══════════════════════════════════════════════
.tc-main {
  max-width: 640px;
  margin: -20px auto 0;
  padding: 0 16px 48px;
  position: relative;
  z-index: 2;
}

// ═══════════════════════════════════════════════
//  搜索卡片
// ═══════════════════════════════════════════════
.tc-search-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,.08);
  margin-bottom: 20px;
}
.tc-search-inner {
  display: flex;
  gap: 8px;
  align-items: center;
}
.tc-search-input {
  flex: 1;
  height: 46px;
  border: 1.5px solid var(--gray-200);
  border-radius: 10px;
  padding: 0 14px;
  font-size: 14px;
  outline: none;
  transition: all .2s;
  background: var(--gray-25);
  &:focus {
    border-color: var(--main-400);
    background: #fff;
    box-shadow: 0 0 0 3px rgba(173,92,94,.1);
  }
}
.tc-search-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.tc-btn-query, .tc-btn-scan {
  height: 46px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  font-weight: 600;
  padding: 0 16px;
  transition: all .2s;
  &:disabled { opacity: .4; cursor: not-allowed; }
}
.tc-btn-query {
  background: var(--main-700);
  color: #fff;
  &:hover:not(:disabled) { background: var(--main-600); }
}
.tc-btn-scan {
  background: var(--gray-100);
  color: var(--gray-700);
  &:hover { background: var(--gray-150); }
  &.active { background: var(--main-50); color: var(--main-700); border: 1px solid var(--main-200); }
}

// ── 扫码器 ──
.tc-scanner-wrap {
  padding-top: 16px;
  text-align: center;
}
.tc-scanner {
  width: 100%;
  max-width: 300px;
  margin: 0 auto;
  border-radius: 12px;
  overflow: hidden;
}
.tc-scanner-hint {
  font-size: 12px;
  color: var(--gray-500);
  margin: 8px 0 0;
}

// ── 加载 ──
.tc-loading {
  text-align: center;
  padding: 48px 0;
  color: var(--gray-500);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}
.tc-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--gray-200);
  border-top-color: var(--main-500);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

// ── 错误 ──
.tc-error-card {
  background: var(--color-error-50);
  border: 1px solid var(--color-error-100);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-error-700);
  font-size: 14px;
  margin-bottom: 16px;
}

// ═══════════════════════════════════════════════
//  溯源报告
// ═══════════════════════════════════════════════
.tc-report {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

// ── 校验横幅 ──
.tc-trust-bar {
  border-radius: 14px;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  &.ok {
    background: linear-gradient(135deg, #e6f9e8, #f0fdf2);
    border: 1px solid #b7eb8f;
  }
  &.fail {
    background: linear-gradient(135deg, #fff1f0, #fff5f5);
    border: 1px solid #ffa39e;
  }
}
.tc-trust-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  .tc-trust-bar.ok & { background: #52c41a; color: #fff; }
  .tc-trust-bar.fail & { background: #ff4d4f; color: #fff; }
}
.tc-trust-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  strong {
    font-size: 15px;
    font-weight: 600;
    .tc-trust-bar.ok & { color: #135200; }
    .tc-trust-bar.fail & { color: #820014; }
  }
  span {
    font-size: 12px;
    .tc-trust-bar.ok & { color: #389e0d; }
    .tc-trust-bar.fail & { color: #cf1322; }
  }
}

// ── 时间线 ──
.tc-timeline {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 18px 12px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.tc-tl-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  opacity: .35;
  transition: opacity .3s;
  &.active { opacity: 1; }
  span { font-size: 12px; font-weight: 500; color: var(--gray-700); }
  small { font-size: 11px; color: var(--gray-400); }
}
.tc-tl-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--gray-100);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-400);
  .tc-tl-step.active & {
    background: var(--main-50);
    color: var(--main-600);
    box-shadow: 0 0 0 2px var(--main-200);
  }
}
.tc-tl-line {
  width: 32px;
  height: 2px;
  background: var(--gray-200);
  margin: 0 4px;
  margin-bottom: 20px;
}

// ═══════════════════════════════════════════════
//  卡片
// ═══════════════════════════════════════════════
.tc-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,.04);
  overflow: hidden;
}
.tc-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px 0;
  h3 {
    font-size: 15px;
    font-weight: 600;
    color: var(--gray-800);
    margin: 0;
  }
}
.tc-card-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tc-icon-green { background: #e6f9e8; color: #389e0d; }
.tc-icon-orange { background: #fff7e6; color: #d46b08; }
.tc-icon-blue { background: #e6f4ff; color: #0958d9; }
.tc-icon-purple { background: #f9f0ff; color: #722ed1; }

.tc-card-body {
  padding: 14px 18px 18px;
}

// ── 行 ──
.tc-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 8px 0;
  & + .tc-row { border-top: 1px solid var(--gray-50); }
}
.tc-row-label {
  font-size: 13px;
  color: var(--gray-500);
  flex-shrink: 0;
}
.tc-row-value {
  font-size: 13px;
  color: var(--gray-800);
  text-align: right;
  word-break: break-all;
}
.tc-value-highlight {
  font-weight: 600;
  color: var(--main-700);
}
.tc-value-mono {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  color: var(--gray-600);
}

// ── 等级徽章 ──
.tc-grade-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  background: linear-gradient(135deg, #fff7e6, #ffe7ba);
  color: #d46b08;
  border: 1px solid #ffd591;
}

// ── 质检 ──
.tc-insp-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--gray-25);
  border-radius: 10px;
  & + .tc-insp-row { margin-top: 8px; }
}
.tc-insp-type {
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-800);
}
.tc-insp-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--color-error-50);
  color: var(--color-error-700);
  &.pass { background: #e6f9e8; color: #135200; }
}
.tc-insp-lab {
  font-size: 12px;
  color: var(--gray-500);
  margin-left: auto;
}

// ── 田间管理时间线 ──
.tc-activity-list {
  padding-left: 4px;
}
.tc-act-item {
  display: flex;
  gap: 14px;
  position: relative;
  padding-bottom: 16px;
  &::before {
    content: '';
    position: absolute;
    left: 5px;
    top: 14px;
    bottom: 0;
    width: 1.5px;
    background: var(--gray-200);
  }
  &:last-child {
    padding-bottom: 0;
    &::before { display: none; }
  }
}
.tc-act-dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--main-400);
  flex-shrink: 0;
  margin-top: 4px;
  position: relative;
  z-index: 1;
  box-shadow: 0 0 0 3px var(--main-50);
}
.tc-act-content {
  flex: 1;
  min-width: 0;
}
.tc-act-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.tc-act-type {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
}
.tc-act-date {
  font-size: 12px;
  color: var(--gray-400);
  flex-shrink: 0;
}
.tc-act-detail {
  font-size: 13px;
  color: var(--gray-600);
  margin: 3px 0 0;
  line-height: 1.5;
}
.tc-act-materials {
  font-size: 12px;
  color: var(--gray-400);
  margin: 2px 0 0;
}

// ── 照片 ──
.tc-photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.tc-photo-item {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  aspect-ratio: 4/3;
  background: var(--gray-100);
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}
.tc-photo-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(0,0,0,.5);
  color: #fff;
  backdrop-filter: blur(4px);
}

// ── 校验详情 ──
.tc-card-verify {
  background: var(--gray-25);
  box-shadow: none;
  border: 1px solid var(--gray-100);
}
.tc-verify-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 13px;
  color: var(--gray-600);
  & + .tc-verify-item { border-top: 1px solid var(--gray-100); }
}
.tc-verify-tag {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--gray-100);
  color: var(--gray-600);
  &.ok { background: #e6f9e8; color: #135200; }
  &.fail { background: #fff1f0; color: #820014; }
}

// ── 底部 ──
.tc-footer {
  text-align: center;
  padding: 24px 0 8px;
  p {
    font-size: 12px;
    color: var(--gray-400);
    letter-spacing: 1px;
    margin: 0;
  }
}

// ═══════════════════════════════════════════════
//  过渡动画
// ═══════════════════════════════════════════════
.fade-enter-active { transition: opacity .3s ease; }
.fade-enter-from { opacity: 0; }

.fade-up-enter-active { transition: all .4s ease; }
.fade-up-enter-from { opacity: 0; transform: translateY(12px); }

.slide-down-enter-active { transition: all .3s ease; }
.slide-down-enter-from { opacity: 0; max-height: 0; overflow: hidden; }

// ═══════════════════════════════════════════════
//  响应式
// ═══════════════════════════════════════════════
@media (max-width: 480px) {
  .tc-hero { padding: 36px 16px 32px; }
  .tc-hero-title { font-size: 24px; }
  .tc-hero-slogan { font-size: 14px; }
  .tc-main { padding: 0 12px 36px; }
  .tc-search-inner { flex-wrap: wrap; }
  .tc-search-input { width: 100%; }
  .tc-search-actions { width: 100%; }
  .tc-btn-scan, .tc-btn-query { flex: 1; }
  .tc-timeline { padding: 14px 8px; }
  .tc-tl-line { width: 20px; }
  .tc-card-header { padding: 14px 14px 0; }
  .tc-card-body { padding: 12px 14px 14px; }
  .tc-info-grid { grid-template-columns: 1fr; }
}
</style>
