# 番茄温室智能管控平台

## 这是什么

一个专门为番茄温室种植打造的 AI 智能管控平台。它接入了温室内空气传感器、土壤传感器和执行器设备，由 AI 智能体实时分析环境数据，自主做出调控决策，并直接操作设备执行。平台覆盖了从环境监测、生长追踪、成熟度分析到采收调度的完整种植流程，帮助温室管理者实现精准化、自动化的番茄种植管理。

## 它能做什么

### 实时环境监测与预警
平台实时采集温室内空气温湿度、CO2 浓度、光照强度、土壤 pH 值、EC 值、氮磷钾含量等多项指标，与番茄各生长阶段的适宜参数自动对比。当某项指标偏离正常范围时，AI 会标记预警并给出具体调控建议。

### AI 自动控制设备
温室内的风机、湿帘、通风窗、循环泵等执行器可以通过平台手动控制，也可以切换到 AI 模式。在 AI 模式下，智能体每 60 秒自动巡检一次环境数据，当发现温度偏高时自动开启风机和湿帘降温，CO2 偏低时自动补充，光照不足时发出提醒——实现无人值守的闭环管控。

### 生长全周期管理
从花芽分化、开花、膨果、转色到采收，每个阶段都有对应的 AI 子智能体提供养护建议。系统记录每个棚区的生长阶段、环境变化和农事操作历史，形成完整的生长档案。

### 成熟度扫描与采收调度
使用 YOLO 模型自动识别番茄成熟度，统计各棚区的成熟比例。管理者可以自定义采摘阈值，当某区域成熟度达标后，系统自动提示并生成分区采收计划。

### 全局 AI 助手
平台右下角有一个悬浮的番茄小球，点击后从侧面滑出对话窗口。用户可以随时向 AI 提问——"B 区温度为什么偏高"、"今天需要采摘哪些区域"、"最近一周的生长趋势如何"——AI 会根据实时传感器数据、知识库文档和历史记录综合回答。回复过程中可以看到 AI 调用了哪些工具、查阅了哪些知识库文档，引用的信息来源都可以点击查看原文摘录。

### 知识库 RAG 检索
支持上传番茄种植技术文档、病虫害防治手册、施肥指南等资料构建知识库。AI 在回答问题时会自动检索相关知识库内容，所有回答都带引用标注，可以追溯每一条建议的来源依据。

## 智能体分工

平台设有 1 个总决策智能体和 6 个专业子智能体，各司其职：

| 智能体 | 职责 |
| --- | --- |
| 温室总管 | 统筹调度，根据问题类型分派给合适的子智能体 |
| 仪表盘分析员 | 分析驾驶舱环境数据，生成每日调控建议和预警 |
| IoT 管控员 | 管理物联网设备，AI 模式下直接控制执行器 |
| 天气分析员 | 获取和分析天气数据，评估对温室的影响 |
| 生长顾问 | 跟踪番茄生长阶段，提供养护和农事建议 |
| 成熟度分析员 | 分析成熟度检测数据，生成分区采摘建议 |
| 种植顾问 | 制定采收调度方案和种植决策 |

每个页面的顶部可以切换管辖该页面的子智能体。悬浮球中的 AI 对话由温室总管自动判断问题的性质，调度最合适的子智能体来回答。

## 页面一览

- **番茄驾驶舱**——温室整体态势，环境指标卡片，AI 每日建议
- **智能温室物联网**——传感器实时数据，执行器手动/AI 控制面板
- **生长档案**——各棚区生长阶段记录，AI 养护建议
- **成熟度管理中心**——摄像头拍照检测，成熟度统计，采摘建议
- **采收调度**——采收任务派发与执行追踪
- **AI 决策日志**——全平台 AI 对话历史，决策追溯

---

## 快速开始

### 环境要求

- Docker Desktop (Windows/Mac) 或 Docker Engine (Linux)
- 至少 8GB 内存
- 摄像头（用于成熟度检测）

### 首次启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd Newsmart-Strawberry

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写大模型 API Key 和管理员密码

# 3. 构建并启动所有服务
docker compose up -d --build

# 4. 等待服务启动完成（约1-2分钟）

# 5. 启动本地检测服务（用于摄像头功能）
python scripts/run_detect_local.py

# 6. 访问系统
# 浏览器打开 http://localhost:5173
# 管理员账号: admin / admin123
```

### 日常启动

```bash
# 启动 Docker 服务
docker compose up -d

# 启动本地检测服务（新终端）
python scripts/run_detect_local.py
```

### 日常停止

```bash
# 停止 Docker 服务
docker compose down

# 本地检测服务：Ctrl+C 停止
```

### 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker logs api-dev -f          # API 日志
docker logs mosquitto -f        # MQTT 日志

# 重启单个服务
docker compose restart api

# 重新构建并启动
docker compose up -d --build

# 进入容器调试
docker exec -it api-dev bash
```

---

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 5173 | Vue 3 界面 |
| API | 5050 | FastAPI 后端 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |
| Milvus | 19530 | 向量数据库 |
| Neo4j | 7687 | 知识图谱 |
| MinIO | 9000 | 文件存储 |
| Mosquitto | 1883 | MQTT Broker |
| 本地检测服务 | 8081 | YOLO 检测 |

---

## 代码结构

```
Newsmart-Strawberry/
├── backend/                    # 后端代码
│   ├── package/yuxi/           # 核心包
│   │   ├── agents/             # AI 智能体
│   │   ├── detect/             # 🎯 YOLO 成熟度检测
│   │   ├── iot/                # 📡 MQTT 物联网
│   │   ├── knowledge/          # 📚 知识库 RAG
│   │   ├── traceability/       # 🔗 溯源系统
│   │   └── services/           # 业务服务
│   └── server/                 # FastAPI 服务
│       └── routers/            # API 路由
├── web/                        # 前端代码 (Vue 3)
│   └── src/
│       ├── apis/               # API 接口
│       ├── views/              # 页面
│       └── components/         # 组件
├── esp32/                      # 🔌 ESP32 固件
│   └── main.py                 # 单片机代码
├── scripts/                    # 独立脚本
│   └── run_detect_local.py     # 本地检测服务
└── docker-compose.yml          # Docker 编排
```

### 关键模块位置

#### 🎯 YOLO 成熟度检测

| 功能 | 文件路径 |
|------|----------|
| 核心检测逻辑 | `backend/package/yuxi/detect/core.py` |
| 摄像头管理 | `backend/package/yuxi/detect/camera.py` |
| 数据结构 | `backend/package/yuxi/detect/schemas.py` |
| YOLO 模型文件 | `backend/package/yuxi/detect/models/best.pt` |
| API 路由 | `backend/server/routers/detect_router.py` |
| 业务服务 | `backend/package/yuxi/services/detect_service.py` |
| 前端页面 | `web/src/views/TomatoMaturityCenterView.vue` |
| 前端 API | `web/src/apis/detect_api.js` |
| 本地检测服务 | `scripts/run_detect_local.py` |

#### 📡 MQTT 物联网

| 功能 | 文件路径 |
|------|----------|
| MQTT 客户端 | `backend/package/yuxi/iot/mqtt_client.py` |
| 数据结构 | `backend/package/yuxi/iot/schemas.py` |
| API 路由 | `backend/server/routers/iot_router.py` |
| 业务服务 | `backend/package/yuxi/services/iot_service.py` |
| 前端页面 | `web/src/views/IoTDashboardView.vue` |

#### 📚 知识库 RAG

| 功能 | 文件路径 |
|------|----------|
| 知识库管理 | `backend/package/yuxi/knowledge/` |
| 向量检索 | `backend/package/yuxi/knowledge/manager.py` |
| AI 工具调用 | `backend/package/yuxi/agents/toolkits/knowledge/tools.py` |

#### 🔗 溯源系统

| 功能 | 文件路径 |
|------|----------|
| 区块链核心 | `backend/package/yuxi/traceability/blockchain.py` |
| 数据库操作 | `backend/package/yuxi/traceability/db.py` |
| API 路由 | `backend/server/routers/trace_router.py` |
| 前端页面 | `web/src/views/TraceabilityView.vue` |

#### 🔌 ESP32 固件

| 功能 | 文件路径 |
|------|----------|
| ESP32 主程序 | `esp32/main.py` |
| 配置文件 | `esp32/config.json`（运行时生成）|

---

## ESP32 硬件配置

### 配网步骤

1. **给 ESP32 上电**
2. **手机连接热点** `A-strawberry` (密码: `12345678`)
3. **浏览器打开** `http://192.168.4.1`
4. **修改配置**：
   - WiFi SSID: 你的 WiFi 名称
   - WiFi Password: 你的 WiFi 密码
   - MQTT Server: 电脑局域网 IP（如 `192.168.1.100`）
   - MQTT User: 留空
   - MQTT Password: 留空
5. **保存重启**

### MQTT Topic

| Topic | 方向 | 说明 |
|-------|------|------|
| `/air/post` | ESP32 → 服务器 | 空气传感器数据 |
| `/soil/post` | ESP32 → 服务器 | 土壤传感器数据 |
| `strawberry_irrigation` | 服务器 → ESP32 | 灌溉控制指令 |
| `strawberry_fan` | 服务器 → ESP32 | 风扇控制指令 |

### 查看电脑 IP

```bash
# Windows
ipconfig | findstr "IPv4"

# Linux/Mac
ifconfig | grep "inet"
```

---

## 常见问题

### Q: 检测功能不工作？

1. 确保本地检测服务已启动：`python scripts/run_detect_local.py`
2. 检查摄像头是否被其他程序占用
3. 查看日志：本地检测服务控制台输出

### Q: MQTT 连接失败？

1. 确保 Mosquitto 服务运行：`docker compose ps`
2. 检查防火墙是否允许 1883 端口
3. 网络设置为"专用网络"（Windows）

### Q: 传感器数据不更新？

1. 检查 ESP32 是否连接 WiFi 和 MQTT
2. 确认 MQTT 地址配置正确
3. 查看 ESP32 串口日志

### Q: 服务启动失败？

```bash
# 查看详细日志
docker compose logs api

# 重新构建
docker compose up -d --build
```

---

## 技术栈

- **前端**：Vue 3 + Vite + Ant Design Vue
- **后端**：FastAPI + LangGraph + SQLAlchemy
- **数据库**：PostgreSQL + Redis + Milvus + Neo4j
- **文件存储**：MinIO
- **物联网**：MQTT (Mosquitto)
- **AI 模型**：大语言模型 + YOLO 目标检测
- **硬件**：ESP32 + RS485 传感器 + 继电器
- **部署**：Docker Compose

---

## 许可证

MIT License
