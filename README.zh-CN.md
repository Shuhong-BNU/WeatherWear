# WeatherWear 3.0

WeatherWear 3.0 是一个围绕“地点确认 -> 天气查询 -> 穿搭建议 -> 可观测执行链路”构建的 LLM 应用工程项目。  
它的重点不是做通用 Agent 平台，而是把一个真实、可运行的天气穿搭应用打磨成：

- 前后端完整
- 主链路清晰
- 轻量 RAG 可验证
- 调试信息可追踪
- 可以本机运行，也可以临时公网分享

的工程化系统。

## 1. 项目定位

WeatherWear 最准确的定位是：

> 一个面向天气穿搭场景的、带 workflow 编排、轻量 RAG 和可观测执行链路的 LLM 应用工程。

它强调的是：

- `workflow`
- `lightweight RAG`
- `observability`
- `code-orchestrated tool calls`

它不强调的是：

- 通用 Agent 平台
- 多 Agent 协作
- 长期记忆系统
- 真正多模态大模型
- 正式生产闭环

## 2. 架构分层

建议把整个项目理解成 6 层：

1. 前端交互层 `Frontend Interaction Layer`
2. API 接入层 `API Access Layer`
3. Workflow / Coordinator 编排层 `Workflow / Coordinator Orchestration Layer`
4. Domain Services 能力层 `Domain Services Layer`
5. Retrieval / Knowledge 层 `Retrieval / Knowledge Layer`
6. Runtime / Observability / Storage 层 `Runtime / Observability / Storage Layer`

### 2.1 前端交互层

职责：

- 文本查询
- 地图选点
- 候选地点确认
- 结果展示
- 历史与收藏
- 开发者页面

关键位置：

- `frontend/src/app/AppRouter.tsx`
- `frontend/src/app/state/WeatherWearSession.tsx`
- `frontend/src/features/query/*`
- `frontend/src/features/results/*`
- `frontend/src/features/map/*`

### 2.2 API 接入层

职责：

- 暴露查询接口
- 暴露设置、日志、开发者会话、历史、收藏接口
- 在 `frontend/dist` 存在时直接托管前端页面和静态资源

关键位置：

- `weatherwear/api/server.py`

### 2.3 Workflow / Coordinator 编排层

职责：

- 决定走 fast path 还是 supervisor planner
- 组织固定节点图执行
- 管理取消、trace、步骤记录和 finalize

关键位置：

- `weatherwear/application/coordinator.py`
- `weatherwear/application/workflow.py`

### 2.4 Domain Services 能力层

职责：

- 城市解析
- 天气服务
- 场景提取
- 穿搭建议生成
- 结果视图组装

关键位置：

- `weatherwear/services/city_resolver.py`
- `weatherwear/services/weather_service.py`
- `weatherwear/services/occasion_parser.py`
- `weatherwear/services/fashion_agent.py`
- `weatherwear/application/presentation.py`

### 2.5 Retrieval / Knowledge 层

职责：

- 本地 JSONL 穿搭知识库
- 规则检索
- 向量检索
- rerank
- Chroma / 本地向量缓存降级

关键位置：

- `weatherwear/services/fashion_knowledge.py`
- `weatherwear/resources/fashion_knowledge/*.jsonl`

### 2.6 Runtime / Observability / Storage 层

职责：

- 运行时状态
- 日志与事件
- metrics snapshot
- 历史 / 收藏
- share demo 运行信息

关键位置：

- `.runtime/`
- `weatherwear/support/runtime_storage.py`
- `weatherwear/support/user_state_store.py`
- `weatherwear/support/observability.py`

## 3. 核心功能

- 城市解析与候选确认
- OpenWeather 天气查询
- 基于天气和场景的穿搭建议生成
- 本地 JSONL 穿搭知识库检索
- 开发者工具页：
  - Model Config
  - Map Config
  - System Status
  - Logs
  - Trace / Timeline / Debug
- 中英文界面切换
- 历史记录与收藏地点
- 本机 + 公网临时 demo 分享

## 4. 当前能力边界

### 已实现

- 单场景工作流编排
- 轻量 RAG
- LangGraph 兼容执行
- LLM + 规则双路线生成
- 开发者可观测性
- 中英文支持
- 历史 / 收藏持久化
- 基于 Cloudflare Quick Tunnel 的临时公网分享

### 部分实现

- 向量检索与降级链
- planner 节点式任务拆解
- MCP 可选扩展

### 未实现

- 长期记忆系统
- 真正多模态大模型
- 通用 Agent 平台
- 多 Agent 协作
- 标准 ReAct / Reflexion
- 正式生产级部署闭环

## 5. 技术栈概览

### 前端

- `React 18`
- `TypeScript`
- `Vite`
- `React Router DOM`
- `@tanstack/react-query`
- `i18next`
- `Leaflet / react-leaflet`
- `Tailwind CSS`
- `Vitest`

### 后端

- `Python`
- `FastAPI`
- `Pydantic v2`
- `Uvicorn`
- `requests`
- `python-dotenv`

### AI / RAG

- `LangGraph`
- `LangChain`
- `langchain-openai`
- `ChromaDB`
- 本地 `JSONL` 知识库

### 外部与工程化

- `OpenWeather API`
- `OpenAI-compatible LLM / Embedding Provider`
- `OpenStreetMap`
- 可选 `Baidu Map JS SDK`
- 可选 `FastMCP`
- `PowerShell` 脚本
- `.runtime`
- `cloudflared`

## 6. 仓库结构说明

| 路径 | 说明 |
|---|---|
| `weatherwear/` | 后端主应用，包含 API、workflow、services、support、resources |
| `frontend/` | React 前端，包含查询页、地图交互、结果页、开发者页面 |
| `docs/` | 架构图、图示文档、评审文档与项目说明 |
| `scripts/` | 启动、校验、知识库维护、分享 demo 等脚本 |
| `tests/` | Python 测试用例 |

常用脚本：

| 脚本 | 说明 |
|---|---|
| `scripts/dev_up.py` | 推荐的跨平台统一启动入口 |
| `scripts/dev_down.py` | 停止 `dev_up.py` 启动的前后端进程 |
| `scripts/share_demo.py` | 启动临时公网 demo 分享 |
| `scripts/share_demo_down.py` | 关闭临时公网 demo 分享 |
| `scripts/validate_project.py` | 发布前自检入口 |
| `run_all.ps1` | Windows 单窗口启动前后端 |
| `run_all_dev.ps1` | Windows 双窗口开发模式 |

## 7. 本地运行

### 7.1 推荐启动方式

安装好 Python 和前端依赖后，推荐使用统一入口：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
.\.venv\Scripts\python.exe scripts/dev_up.py
```

如果当前环境使用 `python` 命令，也可以：

```bash
python scripts/dev_up.py
```

停止命令：

```powershell
.\.venv\Scripts\python.exe scripts/dev_down.py
```

### 7.2 运行模式说明

- 未配置 `OPENWEATHER_API_KEY` 时，天气会走 `demo / degraded`
- 未完整配置 LLM 时，planner、穿搭生成或 embedding 可能会走兜底逻辑
- 启动器会打印前端地址、API 地址、当前运行模式和开发者 PIN
- Windows 用户仍可继续使用 `run_all.ps1 / run_all_dev.ps1`

### 7.3 环境变量

复制 `.env.example` 为 `.env`，至少补齐：

```env
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL_ID=
OPENWEATHER_API_KEY=
```

如果不配置 embedding，系统仍可运行，只是知识检索会停留在规则检索模式。

## 8. 公网临时分享 Demo

当前代码支持一种非常实用的演示方式：

- 你自己继续在本机使用 WeatherWear
- 同时把它分享成一个临时 HTTPS 链接给别人访问

### 8.1 启动分享

```powershell
.\.venv\Scripts\python.exe scripts/share_demo.py
```

### 8.2 关闭分享

```powershell
.\.venv\Scripts\python.exe scripts/share_demo_down.py
```

如果要在关闭分享的同时顺便停掉本机应用：

```powershell
.\.venv\Scripts\python.exe scripts/share_demo_down.py --stop-app
```

### 8.3 这项能力的工作方式

脚本会：

- 复用已经启动的 WeatherWear，或先自动启动本机应用
- 读取 `.runtime/ports.json`
- 如果 `frontend/dist` 存在且前端 dev server 不可用，则退回由 FastAPI 直接托管前端
- 使用 `cloudflared` 启动 Cloudflare Quick Tunnel
- 打印本机地址和公网地址

### 8.4 重要说明

- 依赖 `cloudflared`
- 使用的是 Cloudflare Quick Tunnel
- 适合 testing / development / quick demo
- 不是正式生产托管方案
- 电脑关机、断网或关闭 tunnel 后，别人将无法继续访问

## 9. 主链路说明

核心链路如下：

```text
/api/query
  -> coordinator.process_query
  -> city resolution
  -> weather service
  -> fashion_knowledge.retrieve_knowledge_hits
  -> fashion_agent
  -> presentation.build_result_view_model
  -> frontend session state / result UI
```

关键文件：

- `weatherwear/api/server.py`
- `weatherwear/application/coordinator.py`
- `weatherwear/application/workflow.py`
- `weatherwear/application/presentation.py`
- `weatherwear/services/city_resolver.py`
- `weatherwear/services/weather_service.py`
- `weatherwear/services/fashion_agent.py`
- `weatherwear/services/fashion_knowledge.py`
- `frontend/src/app/state/WeatherWearSession.tsx`

## 10. 轻量 RAG 说明

- 知识源：
  - `weatherwear/resources/fashion_knowledge/zh-CN.jsonl`
  - `weatherwear/resources/fashion_knowledge/en-US.jsonl`
- 检索输入：
  - 天气数值
  - 天气条件
  - 场景描述
  - 标签
  - 性别
  - locale
- 检索方式：
  - 规则检索
  - 向量检索
  - 优先 Chroma
  - Chroma 不可用时退回本地向量缓存
  - embedding 不可用时退回纯规则模式
- 输出位置：
  - 用户结果页
  - 开发者 Debug / Timeline / Logs 页面

## 11. 调试与知识库辅助脚本

### 11.1 离线检索评测

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --pretty
```

使用自定义评测集：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --cases weatherwear/resources/evaluation/retrieval_cases.sample.json `
  --pretty `
  --fail-on-check
```

输出 JSON：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --cases weatherwear/resources/evaluation/retrieval_cases.sample.json `
  --output .runtime/retrieval-eval.json
```

### 11.2 知识库校验 / 索引重建

```powershell
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py --rebuild-index
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py --rebuild-index --force
```

### 11.3 知识库导入 / 规范化

仅校验：

```powershell
.\.venv\Scripts\python.exe scripts/import_fashion_knowledge.py `
  --input weatherwear/resources/examples/fashion_knowledge_import.sample.json `
  --locale en-US `
  --validate-only
```

写出新的 JSONL：

```powershell
.\.venv\Scripts\python.exe scripts/import_fashion_knowledge.py `
  --input your_entries.json `
  --output .runtime/normalized-fashion-knowledge.jsonl `
  --locale en-US
```

向现有 locale 追加：

```powershell
.\.venv\Scripts\python.exe scripts/import_fashion_knowledge.py `
  --input your_entries.json `
  --locale en-US `
  --append
```

## 12. 项目验收

### 12.1 最小验收命令

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

它会依次执行：

- 核心 Python 单测
- 知识库校验
- 离线检索评测
- 前端生产构建

### 12.2 验收标准

- 所有 step 返回 `PASS`
- 最终 summary 中 `failed=0`
- 会生成验收报告：`.runtime/validation-report.json`

## 13. 测试

### Python

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 前端

```powershell
cd frontend
npm test
npm run build
```

## 14. 推荐文档入口

- 总入口：`README.md`
- 英文完整版：`README.en-US.md`
- 图示导航：`docs/architecture-diagrams.md`
- 架构概览：`docs/architecture-overview.md`
- 分享 demo 说明：`docs/share-demo.md`
- 面试手册：`WeatherWear_面试复习手册-2.0.md`
- PRD：`docs/prd-weatherwear-2.0.md`

## 15. 面试 / 作品集可讲证据

- 检索评测样例：`weatherwear/resources/evaluation/retrieval_cases.sample.json`
- 知识库导入样例：`weatherwear/resources/examples/fashion_knowledge_import.sample.json`
- 统一验收入口：`scripts/validate_project.py`
- 架构说明：`docs/architecture-overview.md`
- 检索评测说明：`docs/retrieval-evaluation.md`
- 知识库维护说明：`docs/knowledge-base-maintenance.md`
- 开发者工具页可展示：
  - `Trace / Timeline / Debug`
  - `Model Config`
  - `Map Config`
  - `System Status`
  - `Logs`

## 16. 新人接手建议阅读顺序

1. 先看 `README.md` 或 `README.zh-CN.md`
2. 再看 `weatherwear/api/server.py`
3. 再看 `weatherwear/application/coordinator.py`
4. 再看 `weatherwear/application/workflow.py`
5. 再看 `weatherwear/services/fashion_knowledge.py` 和 `weatherwear/services/fashion_agent.py`
6. 最后看 `weatherwear/application/presentation.py` 和 `frontend/src/app/state/WeatherWearSession.tsx`

## 17. 能力边界说明

### 已实现

- 单应用场景下的 LLM 工作流编排
- 轻量 RAG
- 可观测执行链路
- 代码编排式“工具调用”
- 本机 + 临时公网 demo 分享

### 部分实现

- LangGraph 兼容运行时
- 向量检索与混合检索降级链

### 未实现

- 通用 Agent 平台
- 真正 Multi-Agent 协作
- 开放式多轮自主规划
- 独立 Agent Memory / 学习机制 / 在线反馈闭环
- 正式生产级部署闭环
