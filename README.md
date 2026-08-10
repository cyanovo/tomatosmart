# 番茄温室智能管控平台

本项目是一个面向番茄温室的智能管控平台，集成了 AI 智能体、知识库 RAG、物联网 MQTT、番茄成熟度检测、采收调度和产品溯源能力。

项目推荐使用 Docker Compose 部署。后端、前端、数据库、向量库、图数据库、对象存储、MQTT Broker 和智能体沙盒都会由 Docker 自动启动。

## 快速部署

### 1. 准备环境

请先安装：

- Docker Desktop 或 Docker Engine
- Git
- 至少 8GB 内存，推荐 16GB

Windows 用户建议使用 PowerShell 运行命令。

### 2. 克隆项目

```bash
git clone <repository-url>
cd Newsmart-Strawberry
```

### 3. 初始化配置并预下载镜像

Windows:

```powershell
.\scripts\init.ps1
```

Linux / macOS:

```bash
chmod +x scripts/init.sh
./scripts/init.sh
```

课堂私有仓库已经内置 `.env` 配置。初始化脚本会自动补齐本机专用的 `JWT_SECRET_KEY` 和 `GREENHOUSE_INSTANCE_ID`，并通过国内镜像源预下载公开依赖镜像。

### 4. 构建并启动

```bash
docker compose up -d --build
```

首次启动仍需要构建本项目自己的 `greenhouse-api`、`greenhouse-web` 和 `greenhouse-sandbox-provisioner` 镜像，但公开基础镜像会在上一步优先下载好。启动完成后查看状态：

```bash
docker compose ps
```

所有核心服务显示 `healthy` 或 `Up` 后即可访问。

### 5. 访问系统

- 前端页面：http://localhost:5173
- 后端健康检查：http://localhost:5050/api/system/health
- MinIO 控制台：http://localhost:9001
- Neo4j Browser：http://localhost:7474

首次进入系统时会引导创建管理员账号。

## 中国大陆网络加速

如果学生在中国大陆部署，慢的主要原因通常是 Docker 镜像、Python 包和前端依赖下载。建议按下面顺序处理。

### 推荐方式：使用项目初始化脚本

`scripts/init.ps1` 和 `scripts/init.sh` 会预拉取项目所需的基础镜像，并通过 `scripts/pull_image.*` 使用国内可访问的镜像前缀下载常见镜像。

初始化完成后继续运行：

```bash
docker compose up -d --build
```

### 可用的国内镜像前缀

本项目涉及的常见公开镜像可以通过 DaoCloud 公益镜像前缀下载：

| 原镜像 | 大陆下载地址 |
| --- | --- |
| `python:3.12-slim` | `m.daocloud.io/docker.io/library/python:3.12-slim` |
| `node:24-slim` | `m.daocloud.io/docker.io/library/node:24-slim` |
| `node:24-alpine` | `m.daocloud.io/docker.io/library/node:24-alpine` |
| `nginx:alpine` | `m.daocloud.io/docker.io/library/nginx:alpine` |
| `postgres:16` | `m.daocloud.io/docker.io/library/postgres:16` |
| `redis:7-alpine` | `m.daocloud.io/docker.io/library/redis:7-alpine` |
| `neo4j:5.26` | `m.daocloud.io/docker.io/library/neo4j:5.26` |
| `eclipse-mosquitto:2` | `m.daocloud.io/docker.io/eclipse-mosquitto:2` |
| `milvusdb/milvus:v2.5.6` | `m.daocloud.io/docker.io/milvusdb/milvus:v2.5.6` |
| `minio/minio:RELEASE-2023-03-20T20-16-18Z` | `m.daocloud.io/docker.io/minio/minio:RELEASE-2023-03-20T20-16-18Z` |
| `quay.io/coreos/etcd:v3.5.5` | `m.daocloud.io/quay.io/coreos/etcd:v3.5.5` |
| `ghcr.io/astral-sh/uv:0.7.2` | `m.daocloud.io/ghcr.io/astral-sh/uv:0.7.2` |

项目中部分镜像已经使用国内源：

- sandbox 镜像：火山引擎北京源
- PaddleX 镜像：百度北京源
- MinerU 基础镜像：DaoCloud 镜像源

### 包管理源

项目构建阶段建议使用国内包源：

- 前端依赖使用 `https://registry.npmmirror.com`
- 后端 Python 依赖建议使用清华 PyPI 源
- MinerU 使用阿里云 PyPI 源和 ModelScope 下载模型

如果构建时长时间卡在 `uv sync`、`pip install` 或 `apt-get update`，优先检查 Dockerfile 中是否使用了官方源。大陆网络下建议把 Python、Debian apt、npm/pnpm 都配置为国内源。

## 日常启动与停止

已经构建过之后，日常启动不需要加 `--build`：

```bash
docker compose up -d
```

停止服务：

```bash
docker compose down
```

查看服务：

```bash
docker compose ps
```

查看日志：

```bash
docker logs api-dev -f
docker logs worker-dev -f
docker logs web-dev -f
```

重新构建：

```bash
docker compose up -d --build
```

## 服务端口

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| 前端 | 5173 | Vue 页面 |
| API | 5050 | FastAPI 后端 |
| PostgreSQL | 5432 | 业务数据库 |
| Redis | 6379 | 队列、缓存、运行事件 |
| Milvus | 19530 | 向量数据库 |
| Neo4j | 7687 | 知识图谱 |
| Neo4j Browser | 7474 | 图数据库浏览器 |
| MinIO | 9000 | 对象存储 |
| MinIO Console | 9001 | 对象存储管理界面 |
| Mosquitto | 1883 | MQTT Broker |
| Sandbox Provisioner | 8002 | 智能体沙盒管理 |

## 主要功能

- 番茄驾驶舱：温室态势、环境指标、AI 建议。
- 智能温室物联网：空气/土壤传感器数据、执行器控制、AI 模式。
- AI 决策助手：多智能体协作、工具调用、知识库引用、SubAgents。
- 资料中心：用户工作区文件管理。
- 番茄知识库：上传文档、构建 RAG 知识库、图谱检索。
- 生长档案：棚区生长阶段和农事记录。
- 成熟度管理中心：摄像头或图片检测番茄成熟度。
- 采收调度：采收任务分配与追踪。
- 产品溯源：批次、种子、地块、农事操作和二维码溯源。
- AI 日志：查看平台 AI 对话和决策记录。

## 智能体分工

| 智能体 | 职责 |
| --- | --- |
| 温室总管 | 统筹调度，根据问题类型分派给合适的子智能体 |
| 仪表盘分析员 | 分析驾驶舱环境数据，生成每日调控建议和预警 |
| IoT 管控员 | 管理物联网设备，AI 模式下控制执行器 |
| 天气分析员 | 获取和分析天气数据，评估对温室的影响 |
| 生长顾问 | 跟踪番茄生长阶段，提供养护和农事建议 |
| 成熟度分析员 | 分析成熟度检测数据，生成分区采摘建议 |
| 种植顾问 | 制定采收调度方案和种植决策 |

## 代码结构

```text
Newsmart-Strawberry/
├── backend/
│   ├── server/                 # FastAPI 入口和 HTTP 路由
│   └── package/yuxi/           # 核心业务包
│       ├── agents/             # AI 智能体、工具、Skills、MCP
│       ├── knowledge/          # 知识库、文档解析、向量检索、图谱
│       ├── iot/                # MQTT 物联网
│       ├── detect/             # 番茄成熟度检测
│       ├── traceability/       # 产品溯源
│       ├── services/           # 业务服务层
│       └── repositories/       # 数据访问层
├── web/                        # Vue 3 前端
│   └── src/
│       ├── apis/               # 后端接口封装
│       ├── views/              # 页面
│       ├── components/         # 组件
│       └── stores/             # Pinia 状态
├── esp32/                      # ESP32 固件
├── scripts/                    # 初始化、检查、辅助脚本
├── docker/                     # Dockerfile 和相关配置
└── docker-compose.yml          # 开发环境编排
```

更详细的架构说明见 `ARCHITECTURE.md`。

## ESP32 硬件配置

### 配网步骤

1. 给 ESP32 上电。
2. 手机连接热点 `A-strawberry`，密码 `12345678`。
3. 浏览器打开 `http://192.168.4.1`。
4. 填写 WiFi 和 MQTT 配置。
5. 保存并重启 ESP32。

MQTT Server 填写运行本项目电脑的局域网 IP，例如 `192.168.1.100`。

查看电脑 IP：

```bash
# Windows
ipconfig | findstr "IPv4"

# Linux / macOS
ifconfig | grep "inet"
```

### MQTT Topic

| Topic | 方向 | 说明 |
| --- | --- | --- |
| `/air/post` | ESP32 到服务器 | 空气传感器数据 |
| `/soil/post` | ESP32 到服务器 | 土壤传感器数据 |
| `strawberry_irrigation` | 服务器到 ESP32 | 灌溉控制指令 |
| `strawberry_fan` | 服务器到 ESP32 | 风扇控制指令 |

## 常见问题

### 启动很慢

首次部署会下载多个大镜像并构建后端镜像，属于正常情况。大陆网络建议先运行初始化脚本预拉镜像，并尽量使用稳定网络。

### 服务没有全部 healthy

刚启动时 Milvus、Postgres、API 可能需要一段时间预热。先等待 1-3 分钟，再查看：

```bash
docker compose ps
docker logs api-dev --tail 100
```

### 后端健康检查失败

查看 API 日志：

```bash
docker logs api-dev --tail 200
```

常见原因包括 `.env` 缺少模型 API Key、数据库还未就绪、镜像未完整下载。

### 前端打不开

确认 `web-dev` 正在运行：

```bash
docker compose ps web
docker logs web-dev --tail 100
```

然后访问 http://localhost:5173。

### MQTT 设备没有数据

检查：

- `mosquitto` 容器是否运行。
- ESP32 是否连接到同一局域网。
- ESP32 中 MQTT Server 是否填写为电脑局域网 IP。
- Windows 防火墙是否允许 1883 端口。

### 成熟度检测不可用

检查摄像头权限和检测模型：

- 摄像头没有被其他程序占用。
- `backend/package/yuxi/detect/models/best.pt` 存在。
- API 日志中没有模型加载错误。

## 开发命令

后端测试在容器中运行：

```bash
docker compose exec api uv run --group test pytest test/unit -m "not slow"
```

前端构建：

```bash
docker compose exec web pnpm run build
```

代码格式化：

```bash
docker compose exec api make format
```

## 技术栈

- 前端：Vue 3、Vite、Pinia、Ant Design Vue
- 后端：FastAPI、LangGraph、SQLAlchemy、ARQ
- 数据与存储：PostgreSQL、Redis、Milvus、Neo4j、MinIO
- 物联网：MQTT、Mosquitto、ESP32
- AI 能力：大语言模型、RAG、知识图谱、YOLO 目标检测
- 部署：Docker Compose

## 许可证

MIT License
