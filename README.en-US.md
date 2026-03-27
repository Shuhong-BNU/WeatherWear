# WeatherWear 3.0

WeatherWear 3.0 is an LLM application project built around the chain of **location confirmation -> weather lookup -> outfit advice -> observable execution flow**.  
Its goal is not to be a generic agent platform, but to turn a real weather-and-outfit product into a polished engineering project with a complete frontend/backend stack, a clear execution pipeline, verifiable lightweight RAG, and traceable debugging signals.

## Architecture Diagrams

- Diagram guide: `docs/architecture-diagrams.md`
- Chapter-style architecture doc: `docs/weatherwear-architecture/README.md`
- Mermaid sources:
  - `docs/diagrams/module-relationship.mmd`
  - `docs/diagrams/request-sequence.mmd`
  - `docs/diagrams/data-flow.mmd`
- Regenerate the diagrams:

```powershell
.\.venv\Scripts\python.exe scripts/generate_architecture_diagrams.py
```

- Exported assets:
  - `docs/assets/diagrams/module-relationship.svg`
  - `docs/assets/diagrams/request-sequence.svg`
  - `docs/assets/diagrams/data-flow.svg`
  - `docs/assets/diagrams/module-relationship.png`
  - `docs/assets/diagrams/request-sequence.png`
  - `docs/assets/diagrams/data-flow.png`

### Module Relationship Diagram

![Module Relationship Diagram](docs/assets/diagrams/module-relationship.svg)

### Request Sequence Diagram

![Request Sequence Diagram](docs/assets/diagrams/request-sequence.svg)

### Data Flow Diagram

![Data Flow Diagram](docs/assets/diagrams/data-flow.svg)

## Textbook-style V2 Diagrams

### Technical Architecture Diagram (V2)

![Technical Architecture Diagram (V2)](docs/assets/diagrams/architecture-layered-v2.svg)

### Request Sequence Diagram (V2)

![Request Sequence Diagram (V2)](docs/assets/diagrams/request-sequence-v2.svg)

### Data Flow Diagram (V2)

![Data Flow Diagram (V2)](docs/assets/diagrams/data-flow-v2.svg)

## Project Positioning

- User-facing: enter a city or pick a point on the map to get weather results and outfit advice
- Developer-facing: inspect execution traces, model settings, logs, system status, and map settings
- AI scope: `workflow + lightweight RAG + code-orchestrated tool calls`
- Explicit non-goals: open-ended multi-turn agents, autonomous multi-tool loops, standalone memory, true multi-agent collaboration

## Core Features

- City resolution and candidate confirmation
- OpenWeather-based weather lookup
- Outfit advice generation based on weather and occasion context
- Local JSONL outfit knowledge retrieval
- Developer tools pages for:
  - model configuration
  - map configuration
  - system status
  - logs
  - trace / timeline / debug
- Chinese / English UI switching
- Query history and favorite places

## Tech Stack

### Tech Stack Overview

| Domain | Technology / Tool | What it does in this project | Concrete touchpoint |
|---|---|---|---|
| Frontend framework | `React 18` | Powers the query workspace, result pages, history/favorites pages, and developer-facing views | `frontend/src/app`, `frontend/src/features` |
| Frontend language | `TypeScript` | Adds type safety for frontend state, payloads, result models, and map coordinates | `frontend/src/shared/types.ts`, TS/TSX files |
| Frontend build tool | `Vite` | Provides the local dev server, frontend build, and preview workflow | `frontend/package.json` |
| Frontend routing | `React Router DOM` | Organizes query, history, favorites, logs, model config, and map config routes | `frontend/src/app/AppRouter.tsx` |
| Server-state management | `@tanstack/react-query` | Manages async state for query requests, history, favorites, runtime health, developer session, and map settings | `frontend/src/app/state/WeatherWearSession.tsx` |
| Internationalization | `i18next` / `react-i18next` | Supports Chinese/English UI switching across query, result, map, and developer pages | `frontend/src/i18n/index.ts` |
| Map interaction | `Leaflet` / `react-leaflet` | Supports map pin selection, location display, zooming, and coordinate interaction | `frontend/src/features/map/LocationMapCard.tsx` |
| Optional map provider | `Baidu Map JS SDK` (optional) | Powers the Baidu-map mode for rendering, point selection, and search resolution | `frontend/src/features/map/BaiduMapFrame.tsx` |
| Styling system | `Tailwind CSS` | Builds layouts, cards, buttons, and debug panels quickly | `frontend/src/index.css` |
| CSS toolchain | `PostCSS` / `Autoprefixer` | Supports Tailwind compilation and basic browser compatibility handling | `frontend/postcss.config.cjs` |
| Backend language | `Python` | Hosts the API, workflow, weather service, retrieval logic, outfit generation, logging, and runtime storage | `weatherwear/` |
| API framework | `FastAPI` | Exposes `/api/query`, history, favorites, logs, model config, map config, and health endpoints | `weatherwear/api/server.py` |
| Data modeling | `Pydantic v2` | Defines request/response contracts and validates structured payloads | `weatherwear/api/schemas.py` |
| API runtime | `Uvicorn` | Runs the FastAPI application locally | `weatherwear/api/server.py` |
| External HTTP client | `requests` | Calls OpenWeather and other external HTTP services | `weatherwear/services/weather_service.py` |
| Environment loading | `python-dotenv` | Loads model, weather, and map settings from `.env` | `weatherwear/support/llm_support.py`, `weatherwear/services/weather_service.py` |
| Typing support | `typing_extensions` | Provides Python typing compatibility helpers used by the backend stack | `requirements.txt` |
| Workflow runtime | `LangGraph` | Organizes location resolution, weather lookup, and outfit generation as a graph-based workflow runtime | `weatherwear/application/workflow.py` |
| LLM abstraction layer | `LangChain` / `langchain-core` | Provides the abstraction for model invocation and message handling, but does not define the full app architecture | `weatherwear/support/llm_support.py` |
| Model / embedding access | `langchain-openai` | Connects `ChatOpenAI` and `OpenAIEmbeddings` through an OpenAI-compatible interface | `weatherwear/support/llm_support.py` |
| Vector retrieval | `ChromaDB` (optional) | Works as the vector backend for outfit-knowledge retrieval and falls back when unavailable | `weatherwear/services/fashion_knowledge.py` |
| Local knowledge base | `JSONL` | Stores outfit knowledge entries for rule retrieval and lightweight RAG | `weatherwear/resources/fashion_knowledge/*.jsonl` |
| Weather provider | `OpenWeather API` | Supplies live weather facts and geocoding results | `weatherwear/services/weather_service.py` |
| Model provider | `OpenAI-compatible LLM / Embedding Provider` | Supplies planner, outfit-generation, and embedding capabilities | `.env`, `weatherwear/support/llm_support.py` |
| Tile provider | `OpenStreetMap` | Provides the default map tiles for the Leaflet mode | `.env.example`, frontend map settings |
| Optional MCP integration | `FastMCP` (optional) | Exposes weather-query capability as MCP tools and is not required for the main query path | `weatherwear/integrations/weather_mcp.py` |
| Frontend testing | `Vitest` | Runs frontend component and hook tests | `frontend/package.json`, `frontend/src/test` |
| Frontend interaction testing | `@testing-library/react` / `@testing-library/jest-dom` | Verifies rendering, UI interaction, and state transitions | `frontend/src/test` |
| Frontend test environment | `jsdom` | Simulates a browser DOM for frontend tests | `frontend/package.json` |
| Backend testing | `unittest` / `fastapi.testclient` | Tests API behavior, coordinator logic, weather service, retrieval, and presentation | `tests/` |
| Startup / runtime scripts | `PowerShell` | Handles frontend/backend startup, port probing, developer PIN creation, and runtime file management | `run_api.ps1`, `run_web.ps1`, `run_all.ps1` |
| Frontend local persistence | `sessionStorage` / `localStorage` | Stores locale, view preferences, and the latest frontend result state | `frontend/src/app/state/WeatherWearSession.tsx` |
| Runtime persistence | `.runtime` + `JSON / JSONL` | Persists history, favorites, logs, events, and runtime state | `.runtime/`, `runtime_storage.py`, `user_state_store.py` |

### Frontend

- `React 18`
- `TypeScript`
- `Vite`
- `React Router`
- `@tanstack/react-query`
- `i18next` / `react-i18next`
- `Leaflet` / `react-leaflet`
- `Tailwind CSS`
- `Vitest`

### Backend

- `FastAPI`
- `Pydantic`
- `Uvicorn`
- `requests`
- `python-dotenv`

### AI / Retrieval

- `LangChain`
- `LangGraph` (optional runtime)
- local `JSONL` outfit knowledge base
- `Chroma` (optional vector index)
- local persistent vector cache as a fallback when Chroma is unavailable

### Optional Integrations

- `Baidu Map JS SDK`
- `MCP` (install on demand with `requirements-mcp.txt`)

## Resume-ready Project Name

If this project is represented by only one resume entry, use:

**`WeatherWear | Observable Workflow-based Weather & Outfit LLM Application`**

Why this name fits:

- it accurately frames the project as a **single-scenario LLM application engineering project**
- it highlights the real strengths: `workflow + lightweight RAG + observability`
- it does not overstate the system as a generic agent platform or a true multi-agent collaboration framework

## Repository Layout

```text
frontend/                         React frontend
scripts/                          Development and knowledge-base helper scripts
tests/                            Python tests
docs/                             Architecture, evaluation, and knowledge-base maintenance docs
weatherwear/
  api/                            FastAPI endpoints
  application/                    coordinator / workflow / presentation
  domain/                         Core type definitions
  resources/                      City aliases, evaluation cases, and outfit knowledge
  services/                       Weather, location, outfit, and retrieval services
  support/                        Config, logs, health checks, runtime storage
run_all.ps1                       Start frontend + backend in one window
run_all_dev.ps1                   Two-window development mode
run_api.ps1                       Start API only
run_web.ps1                       Start frontend only
stop_all.ps1                      Stop background processes
```

## Local Setup

### Recommended Startup Path (best for GitHub visitors)

After installing Python and frontend dependencies, the recommended cross-platform entry is:

```powershell
.\.venv\Scripts\python.exe scripts/dev_up.py
```

If your environment uses `python`, this also works:

```bash
python scripts/dev_up.py
```

Stop command:

```powershell
.\.venv\Scripts\python.exe scripts/dev_down.py
```

Notes:

- without `OPENWEATHER_API_KEY`, the app still starts, but weather uses `demo / degraded`
- without a full LLM configuration, planner / outfit generation / embeddings may use fallback logic
- the launcher prints the frontend URL, API URL, current runtime mode, and developer PIN
- Windows users can still use `run_all.ps1 / run_all_dev.ps1`

### 1. Install Python dependencies

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you need MCP:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
```

### 2. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill at least:

```env
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL_ID=
OPENWEATHER_API_KEY=
```

If embedding is not configured, the app still runs, but knowledge retrieval stays in rules-only mode.

### 4. Start the project

#### Single-window mode

```powershell
.\run_all.ps1
```

Highlights:

- starts backend and frontend automatically
- detects available ports automatically
- writes logs into `.runtime/logs/`
- generates a local developer PIN on startup
- opens the browser automatically by default

Skip opening the browser:

```powershell
$env:WEATHERWEAR_SKIP_BROWSER="1"
.\run_all.ps1
```

Stop background processes:

```powershell
.\stop_all.ps1
```

#### Development mode

```powershell
.\run_all_dev.ps1
```

Highlights:

- API and frontend run in separate PowerShell windows
- better for watching logs and debugging in real time

#### Start each side separately

```powershell
.\run_api.ps1
.\run_web.ps1
```

## Pre-push Validation

Before pushing to GitHub, run:

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

## Default Ports and Runtime Files

- frontend defaults to `http://127.0.0.1:5173`
- API defaults to `http://127.0.0.1:8000`
- if a port is occupied, startup scripts choose another free port automatically
- runtime directory: `.runtime/`
- logs directory: `.runtime/logs/`
- structured event log: `.runtime/logs/app.events.jsonl`

## Developer PIN

- `/dev/*` pages require unlocking the developer session first
- the PIN is generated locally by the startup script
- the terminal prints the active PIN after startup

## Core Flow

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

Key files:

- `weatherwear/api/server.py`
- `weatherwear/application/coordinator.py`
- `weatherwear/application/workflow.py`
- `weatherwear/application/presentation.py`
- `weatherwear/services/city_resolver.py`
- `weatherwear/services/weather_service.py`
- `weatherwear/services/fashion_agent.py`
- `weatherwear/services/fashion_knowledge.py`
- `frontend/src/app/state/WeatherWearSession.tsx`

## Lightweight RAG Notes

- knowledge sources: `weatherwear/resources/fashion_knowledge/zh-CN.jsonl` and `weatherwear/resources/fashion_knowledge/en-US.jsonl`
- retrieval inputs: weather values, weather conditions, occasion description, tags, gender, locale
- retrieval modes:
  - rule-based retrieval
  - vector retrieval (prefer Chroma)
  - fallback to local vector cache when Chroma is unavailable
  - fallback to pure rules when embedding is not configured
- outputs are surfaced in:
  - the user-facing result page
  - the developer Debug / Timeline / Logs pages

## Debugging and Knowledge-Base Scripts

### Offline retrieval evaluation

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --pretty
```

Use a custom evaluation set:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --cases weatherwear/resources/evaluation/retrieval_cases.sample.json `
  --pretty `
  --fail-on-check
```

Write JSON output for archiving or portfolio notes:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --cases weatherwear/resources/evaluation/retrieval_cases.sample.json `
  --output .runtime/retrieval-eval.json
```

### Knowledge-base validation / summary / index rebuild

```powershell
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py --rebuild-index
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py --rebuild-index --force
```

### Knowledge-base import / normalization

Validate only, without writing:

```powershell
.\.venv\Scripts\python.exe scripts/import_fashion_knowledge.py `
  --input weatherwear/resources/examples/fashion_knowledge_import.sample.json `
  --locale en-US `
  --validate-only
```

Write a normalized JSONL file:

```powershell
.\.venv\Scripts\python.exe scripts/import_fashion_knowledge.py `
  --input your_entries.json `
  --output .runtime/normalized-fashion-knowledge.jsonl `
  --locale en-US
```

Append into an existing locale knowledge base:

```powershell
.\.venv\Scripts\python.exe scripts/import_fashion_knowledge.py `
  --input your_entries.json `
  --locale en-US `
  --append
```

Recommended maintenance order:

1. Run `scripts/import_fashion_knowledge.py --validate-only`
2. Run `scripts/check_fashion_knowledge.py`
3. If vector cache sync is needed, run `scripts/check_fashion_knowledge.py --rebuild-index`
4. Finally run `scripts/evaluate_retrieval.py --cases weatherwear/resources/evaluation/retrieval_cases.sample.json --pretty`

## Project Validation

### Minimum acceptance command

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

This command runs, in order:

- core Python tests
- knowledge-base validation
- offline retrieval evaluation
- frontend production build

### Success criteria

- every step returns `PASS`
- final summary reports `failed=0`
- the validation report is written to `.runtime/validation-report.json`

## Tests

### Python

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Frontend

```powershell
cd frontend
npm test
npm run build
```

## Good Portfolio / Interview Evidence

- retrieval evaluation sample: `weatherwear/resources/evaluation/retrieval_cases.sample.json`
- import sample: `weatherwear/resources/examples/fashion_knowledge_import.sample.json`
- unified validation entry: `scripts/validate_project.py`
- architecture notes: `docs/architecture-overview.md`
- retrieval evaluation notes: `docs/retrieval-evaluation.md`
- knowledge-base maintenance notes: `docs/knowledge-base-maintenance.md`
- developer pages to demo:
  - `Trace / Timeline / Debug`
  - `Model Config`
  - `Map Config`
  - `System Status`
  - `Logs`

## Recommended Onboarding Order

1. Read `README.md` or `README.en-US.md` first to understand project scope and boundaries
2. Read `weatherwear/api/server.py` to understand the API entry
3. Read `weatherwear/application/coordinator.py` to understand the orchestration chain
4. Read `weatherwear/application/workflow.py` to understand execution routing
5. Read `weatherwear/services/fashion_knowledge.py` and `weatherwear/services/fashion_agent.py`
6. Finish with `weatherwear/application/presentation.py` and `frontend/src/app/state/WeatherWearSession.tsx`

## Capability Boundaries

- Implemented:
  - LLM workflow orchestration for a single application scenario
  - lightweight RAG
  - observable execution flow
  - code-orchestrated “tool calling”
- Partially implemented:
  - LangGraph-compatible runtime
  - vector retrieval and hybrid retrieval fallback chain
- Not implemented:
  - a general agent platform
  - true multi-agent collaboration
  - open-ended autonomous multi-turn planning
  - standalone agent memory / learning / online feedback loops
