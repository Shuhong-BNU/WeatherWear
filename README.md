# WeatherWear 3.0

[中文完整版](README.zh-CN.md) | [Full English Version](README.en-US.md)

---

## 中文

WeatherWear 3.0 是一个围绕“地点确认 -> 天气查询 -> 穿搭建议 -> 可观测执行链路”构建的单场景 LLM 应用工程。  
它的重点是 `workflow + 轻量 RAG + 可观测性`，不是通用 Agent 平台，也不是真正多智能体协作框架。

### 项目定位

- 面向用户：输入城市或在地图上选点，获取天气结果和穿搭建议
- 面向开发：查看执行 trace、模型配置、地图配置、系统状态和日志
- AI 能力边界：`workflow + lightweight RAG + code-orchestrated tool calls`
- 非目标：开放式自治 Agent、长期记忆系统、真正多模态大模型、正式生产级部署闭环

### 架构分层

- 前端交互层 `Frontend Interaction Layer`
- API 接入层 `API Access Layer`
- Workflow / Coordinator 编排层 `Workflow / Coordinator Orchestration Layer`
- Domain Services 能力层 `Domain Services Layer`
- Retrieval / Knowledge 层 `Retrieval / Knowledge Layer`
- Runtime / Observability / Storage 层 `Runtime / Observability / Storage Layer`

### 核心功能

- 城市解析与候选确认
- OpenWeather 天气查询
- 基于天气和场景的穿搭建议生成
- 本地 JSONL 穿搭知识库的轻量 RAG
- 开发者页面：
  - Model Config
  - Map Config
  - System Status
  - Logs
  - Trace / Timeline / Debug
- 中英文切换
- 历史记录与收藏地点
- 基于 Cloudflare Quick Tunnel 的公网临时 demo 分享

### Quick Start

环境要求：

- Python `3.11+`
- Node.js `18+`
- npm `9+`

推荐启动方式：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
.\.venv\Scripts\python.exe scripts/dev_up.py
```

停止命令：

```powershell
.\.venv\Scripts\python.exe scripts/dev_down.py
```

发布前自检：

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

### 公网临时分享 Demo

当前代码支持“本机继续使用 + 公网临时分享”：

```powershell
.\.venv\Scripts\python.exe scripts/share_demo.py
```

关闭分享：

```powershell
.\.venv\Scripts\python.exe scripts/share_demo_down.py
```

说明：

- 该能力依赖 `cloudflared`
- 使用的是 Cloudflare Quick Tunnel
- 更适合 testing / development / quick demo
- 不等于正式生产托管

### 当前代码现状提醒

- `frontend/dist` 存在时，FastAPI 可直接托管前端页面和 `/assets`
- 未配置 `OPENWEATHER_API_KEY` 时，天气会走 `demo / degraded`
- 未完整配置 LLM 时，planner / 穿搭生成 / embedding 会走 fallback
- 当前历史和收藏仍保存在本地 JSON 文件中

### 文档入口

- 中文完整版：[`README.zh-CN.md`](README.zh-CN.md)
- 英文完整版：[`README.en-US.md`](README.en-US.md)
- 图示总览：[`docs/architecture-diagrams.md`](docs/architecture-diagrams.md)
- 架构概览：[`docs/architecture-overview.md`](docs/architecture-overview.md)
- 公网分享说明：[`docs/share-demo.md`](docs/share-demo.md)
- 面试手册：[`WeatherWear_面试复习手册-2.0.md`](WeatherWear_%E9%9D%A2%E8%AF%95%E5%A4%8D%E4%B9%A0%E6%89%8B%E5%86%8C-2.0.md)
- PRD：[`docs/prd-weatherwear-2.0.md`](docs/prd-weatherwear-2.0.md)

---

## English

WeatherWear 3.0 is a single-scenario LLM application project built around **location confirmation -> weather lookup -> outfit advice -> observable execution flow**.  
Its real focus is `workflow + lightweight RAG + observability`, not a generic agent platform or a true multi-agent collaboration framework.

### Project Positioning

- User-facing: enter a city or pick a point on the map to get weather results and outfit advice
- Developer-facing: inspect execution traces, model settings, map settings, system status, and logs
- AI scope: `workflow + lightweight RAG + code-orchestrated tool calls`
- Explicit non-goals: open-ended autonomous agents, standalone memory, true multimodal LLMs, production-grade deployment completion

### Architecture Layers

- Frontend Interaction Layer
- API Access Layer
- Workflow / Coordinator Orchestration Layer
- Domain Services Layer
- Retrieval / Knowledge Layer
- Runtime / Observability / Storage Layer

### Core Features

- City resolution and candidate confirmation
- OpenWeather-based weather lookup
- Outfit advice generation based on weather and occasion context
- Local JSONL outfit knowledge retrieval
- Developer tools pages for:
  - Model Config
  - Map Config
  - System Status
  - Logs
  - Trace / Timeline / Debug
- Chinese / English UI switching
- Query history and favorite places
- Temporary public demo sharing via Cloudflare Quick Tunnel

### Quick Start

Requirements:

- Python `3.11+`
- Node.js `18+`
- npm `9+`

Recommended startup:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
.\.venv\Scripts\python.exe scripts/dev_up.py
```

Stop:

```powershell
.\.venv\Scripts\python.exe scripts/dev_down.py
```

Pre-push validation:

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

### Temporary Public Demo Sharing

This codebase supports a “keep using locally + share publicly” demo flow:

```powershell
.\.venv\Scripts\python.exe scripts/share_demo.py
```

Stop sharing:

```powershell
.\.venv\Scripts\python.exe scripts/share_demo_down.py
```

Notes:

- depends on `cloudflared`
- uses Cloudflare Quick Tunnel
- suitable for testing / development / quick demos
- not a production hosting solution

### Current Code Reality

- when `frontend/dist` exists, FastAPI can directly serve the frontend page and `/assets`
- without `OPENWEATHER_API_KEY`, weather falls back to `demo / degraded`
- without a full LLM config, planner / outfit generation / embedding may use fallback paths
- history and favorites are still persisted in local JSON files

### Docs

- Full Chinese README: [`README.zh-CN.md`](README.zh-CN.md)
- Full English README: [`README.en-US.md`](README.en-US.md)
- Diagram guide: [`docs/architecture-diagrams.md`](docs/architecture-diagrams.md)
- Architecture overview: [`docs/architecture-overview.md`](docs/architecture-overview.md)
- Demo sharing guide: [`docs/share-demo.md`](docs/share-demo.md)
- Interview handbook: [`WeatherWear_面试复习手册-2.0.md`](WeatherWear_%E9%9D%A2%E8%AF%95%E5%A4%8D%E4%B9%A0%E6%89%8B%E5%86%8C-2.0.md)
- PRD: [`docs/prd-weatherwear-2.0.md`](docs/prd-weatherwear-2.0.md)
