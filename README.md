# WeatherWear 3.0

[中文完整版](README.zh-CN.md) | [Full English Version](README.en-US.md)

---

## 中文

WeatherWear 3.0 是一个围绕“地点确认 -> 天气查询 -> 穿搭建议 -> 可观测执行链路”构建的 **单场景 LLM 应用工程项目**。  
它强调 `workflow + 轻量 RAG + 可观测性`，不是通用 Agent 平台，也不是真正多智能体协作框架。

### 简历统一命名

**`WeatherWear｜可观测工作流式天气穿搭 LLM 应用`**

### Quick Start

**环境要求**

- Python `3.11+`
- Node.js `18+`
- npm `9+`

**一键启动步骤**

1. 克隆仓库
2. 安装依赖
3. 运行统一启动命令

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
.\.venv\Scripts\python.exe scripts/dev_up.py
```

如果你的系统命令是 `python`，也可以使用：

```bash
python scripts/dev_up.py
```

**常见运行模式说明**

- 未配置 `OPENWEATHER_API_KEY`：系统仍可启动，但天气会进入 `demo / degraded` 路径
- 未完整配置 LLM：系统仍可启动，但 planner、穿搭生成或 embedding 可能走兜底逻辑
- 开发者 PIN 会自动写入 `.env` 中的 `WEATHERWEAR_DEV_PIN`

**停止命令**

```powershell
.\.venv\Scripts\python.exe scripts/dev_down.py
```

**发布前自检**

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

### 推荐图谱

#### 技术架构图（V3）

![技术架构图（V3）](docs/assets/diagrams/architecture-layered-v3.svg)

#### 请求时序图（V3）

![请求时序图（V3）](docs/assets/diagrams/request-sequence-v3.svg)

#### 数据流转过程图（V3）

![数据流转过程图（V3）](docs/assets/diagrams/data-flow-v3.svg)

更多图示与旧版图入口见：`docs/architecture-diagrams.md`

### 技术栈速览

- 前端：`React 18`、`TypeScript`、`Vite`、`React Router DOM`、`@tanstack/react-query`、`i18next`、`Leaflet / react-leaflet`、`Tailwind CSS`
- 后端：`Python`、`FastAPI`、`Pydantic v2`、`Uvicorn`、`requests`、`python-dotenv`
- AI / RAG：`LangGraph`、`LangChain`、`langchain-openai`、`ChromaDB`、本地 `JSONL` 知识库
- 外部与工程化：`OpenWeather API`、`OpenAI-compatible LLM / Embedding Provider`、`OpenStreetMap`、`Baidu Map JS SDK`（可选）、`FastMCP`（可选）、`PowerShell` 脚本、`.runtime`

完整技术栈总览表见：`README.zh-CN.md` / `README.en-US.md`

### 仓库结构说明

| 路径 | 说明 |
|---|---|
| `weatherwear/` | 后端主应用，包含 API、workflow、服务、support、resources |
| `frontend/` | React 前端，包含查询页、地图交互、结果页、开发者页面 |
| `docs/` | 架构图、图示文档、评审文档与项目说明 |
| `scripts/` | 图生成、校验、启动辅助等脚本 |
| `tests/` | Python 测试用例 |

| 脚本 | 说明 |
|---|---|
| `scripts/dev_up.py` | 推荐的跨平台统一启动入口 |
| `scripts/dev_down.py` | 停止 `dev_up.py` 启动的前后端进程 |
| `scripts/validate_project.py` | 发布前自检入口 |
| `run_all.ps1` | Windows 单窗口启动前后端 |
| `run_all_dev.ps1` | Windows 双窗口开发模式 |

### 文档索引

- 中文完整版：`README.zh-CN.md`
- 英文完整版：`README.en-US.md`
- 图示导航：`docs/architecture-diagrams.md`
- 架构概览：`docs/architecture-overview.md`
- 图谱说明：`docs/weatherwear-architecture/README.md`
- 现有图成品评审：`docs/weatherwear-architecture/diagram-review.md`

### 放到 GitHub 后还能继续让 Codex 调整吗？

可以。最稳的方式是继续在**本地工作区**里让 Codex 修改，再把改动推回 GitHub。  
如果你换了机器或目录，也只需要重新克隆仓库到新的本地工作区，Codex 仍然可以继续接手。

---

## English

WeatherWear 3.0 is a **single-scenario LLM application engineering project** built around **location confirmation -> weather lookup -> outfit advice -> observable execution flow**.  
It emphasizes `workflow + lightweight RAG + observability`; it is not a generic agent platform and not a true multi-agent collaboration framework.

### Resume-ready Project Name

**`WeatherWear | Observable Workflow-based Weather & Outfit LLM Application`**

### Quick Start

**Requirements**

- Python `3.11+`
- Node.js `18+`
- npm `9+`

**Three-step local startup**

1. Clone the repository
2. Install dependencies
3. Run the unified launcher

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
.\.venv\Scripts\python.exe scripts/dev_up.py
```

If your environment uses `python`, this also works:

```bash
python scripts/dev_up.py
```

**Common runtime modes**

- Without `OPENWEATHER_API_KEY`, the app still starts, but weather falls back to `demo / degraded`
- Without full LLM configuration, planner / outfit generation / embeddings may use fallback paths
- The developer PIN is auto-written into `.env` as `WEATHERWEAR_DEV_PIN`

**Stop command**

```powershell
.\.venv\Scripts\python.exe scripts/dev_down.py
```

**Pre-push validation**

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

### Recommended Diagrams

#### Technical Architecture Diagram (V3)

![Technical Architecture Diagram (V3)](docs/assets/diagrams/architecture-layered-v3.svg)

#### Request Sequence Diagram (V3)

![Request Sequence Diagram (V3)](docs/assets/diagrams/request-sequence-v3.svg)

#### Data Flow Diagram (V3)

![Data Flow Diagram (V3)](docs/assets/diagrams/data-flow-v3.svg)

See `docs/architecture-diagrams.md` for the full diagram guide and retained legacy versions.

### Tech Stack Snapshot

- Frontend: `React 18`, `TypeScript`, `Vite`, `React Router DOM`, `@tanstack/react-query`, `i18next`, `Leaflet / react-leaflet`, `Tailwind CSS`
- Backend: `Python`, `FastAPI`, `Pydantic v2`, `Uvicorn`, `requests`, `python-dotenv`
- AI / RAG: `LangGraph`, `LangChain`, `langchain-openai`, `ChromaDB`, local `JSONL` knowledge base
- External & engineering: `OpenWeather API`, `OpenAI-compatible LLM / Embedding Provider`, `OpenStreetMap`, optional `Baidu Map JS SDK`, optional `FastMCP`, `PowerShell` scripts, `.runtime`

See `README.zh-CN.md` / `README.en-US.md` for the full stack overview.

### Repository Map

| Path | Purpose |
|---|---|
| `weatherwear/` | Backend app: API, workflow, services, support, and resources |
| `frontend/` | React frontend: query UI, map interaction, results, developer pages |
| `docs/` | Architecture docs, diagrams, and review materials |
| `scripts/` | Diagram generation, validation, and launcher utilities |
| `tests/` | Python test suite |

| Script | Purpose |
|---|---|
| `scripts/dev_up.py` | Recommended cross-platform unified launcher |
| `scripts/dev_down.py` | Stops the processes started by `dev_up.py` |
| `scripts/validate_project.py` | Pre-push validation entry |
| `run_all.ps1` | Windows single-window startup |
| `run_all_dev.ps1` | Windows two-window development mode |

### Docs Index

- Full Chinese README: `README.zh-CN.md`
- Full English README: `README.en-US.md`
- Diagram guide: `docs/architecture-diagrams.md`
- Architecture overview: `docs/architecture-overview.md`
- Diagram walkthrough: `docs/weatherwear-architecture/README.md`
- Existing-diagram review: `docs/weatherwear-architecture/diagram-review.md`

### Can Codex keep helping after this repo is on GitHub?

Yes. The most reliable workflow is to keep using Codex on your **local workspace**, then push changes back to GitHub.  
If you move to another machine or folder, just clone the repo again into a new local workspace and Codex can continue from there.
