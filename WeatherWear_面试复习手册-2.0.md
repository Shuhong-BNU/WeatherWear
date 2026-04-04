# WeatherWear3.0 面试复习手册

## 1. 项目定位

这个项目最准确的定位，不是“通用 Agent 平台”，而是一个围绕：

- 地点确认
- 天气查询
- 穿搭建议生成
- 可观测执行链路

构建出来的单场景 LLM 应用工程。

它的核心价值不只是“接了大模型 API”，而是把一个真实产品场景做成了有完整前后端、有工作流编排、有轻量 RAG、有降级链、有开发者调试页面的工程化系统。

一句话概括：

> 这是一个以 workflow 为骨架、以天气穿搭场景为目标、以轻量 RAG 和可观测性为亮点的 LLM 应用工程项目。

面试里建议特别强调两点：

- 它不是开放式自治 Agent，而是受控编排的工作流系统
- 它的强项是工程完整度、执行链路透明度和降级稳定性

## 2. 整体架构

这个项目可以拆成 6 层来看：

1. 前端交互层
2. API 接入层
3. Workflow / Coordinator 编排层
4. Domain Services 能力层
5. Retrieval / Knowledge 层
6. Runtime / Observability / Storage 层

### 2.1 前端交互层

前端是一个完整的 React 应用，不只是一个演示页。

主要负责：

- 文本查询
- 地图选点查询
- 城市候选确认
- 结果展示
- 历史与收藏
- 开发者页面

核心文件：

- `frontend/src/app/AppRouter.tsx`
- `frontend/src/app/state/WeatherWearSession.tsx`
- `frontend/src/features/query/*`
- `frontend/src/features/results/*`
- `frontend/src/features/map/*`

前端除了用户页面，还有一组开发者页面：

- Trace
- Timeline / Debug
- Model Config
- Map Config
- System Status
- Logs

这说明它不是只做“能跑起来”，而是已经考虑了可调试、可解释和运行态可视化。

### 2.2 API 接入层

后端入口是 FastAPI。

WeatherWear 当前最核心的 API 包括：

- `GET /api/health/runtime`
- `GET /api/examples`
- `POST /api/query`
- `POST /api/query/cancel`
- `GET /api/settings/model`
- `PUT /api/settings/model`
- `POST /api/settings/model/test`
- `GET /api/settings/map`
- `PUT /api/settings/map`
- `POST /api/settings/map/test`
- `GET /api/history`
- `POST /api/history`
- `DELETE /api/history/{item_id}`
- `GET /api/favorites`
- `POST /api/favorites`
- `DELETE /api/favorites/{item_id}`
- `GET /api/logs/sources`
- `GET /api/logs/tail`
- `GET /api/dev/session`
- `POST /api/dev/unlock`
- `POST /api/dev/lock`

核心入口文件：

- `weatherwear/api/server.py`

其中：

- `/api/query` 是主链路入口
- `/api/settings/*` 体现模型和地图的可配置性
- `/api/logs/*` 和 `/api/health/runtime` 体现可观测性
- `/api/history`、`/api/favorites` 提供用户侧状态持久化

另外，当前代码里还支持：

- 当 `frontend/dist` 存在时，由 FastAPI 直接提供 `/`
- 直接挂载 `/assets`
- 其余非 `/api/*` 路由走前端 SPA fallback

这让项目除了开发态前端之外，还具备“后端直接托管前端产物”的能力。

### 2.3 Workflow / Coordinator 编排层

这层是 WeatherWear 最像“智能体系统”的地方。

核心类和文件：

- `weatherwear/application/coordinator.py`
- `weatherwear/application/workflow.py`

这里做的事情不是让模型开放式自由行动，而是：

- 接收查询上下文
- 决定走 fast path 还是 supervisor planner
- 跑固定节点图
- 在节点之间做条件路由
- 汇总 execution trace
- 统一 finalize 结果

固定节点主要包括：

- `planner`
- `resolve_city`
- `fetch_weather`
- `generate_outfit`
- `clarify_city`
- `finalize`

所以它更准确的说法是：

> 有 “Agent 风格元素” 的 workflow 编排器，而不是通用自治 Agent。

### 2.4 Domain Services 能力层

这层承担真正的业务能力。

主要包括：

- `city_resolver.py`
  - 城市别名、候选解析、歧义澄清、候选验证
- `weather_service.py`
  - 地理编码、反向地理编码、实时天气、指定日期天气、demo weather 降级
- `occasion_parser.py`
  - 从场景文本中提取标签和主场景
- `fashion_agent.py`
  - 基于天气 + 场景 + 知识命中生成穿搭建议
- `fashion_knowledge.py`
  - 规则检索、向量检索、rerank、知识应用
- `presentation.py`
  - 把结果整理成前端可直接消费的 view model

这层说明项目不是把所有逻辑都塞进 prompt 里，而是把关键步骤拆成明确的 service。

### 2.5 Retrieval / Knowledge 层

这层是 WeatherWear 的轻量 RAG 核心。

数据源：

- `weatherwear/resources/fashion_knowledge/zh-CN.jsonl`
- `weatherwear/resources/fashion_knowledge/en-US.jsonl`

支持的能力：

- 规则检索
- 向量检索
- rerank
- knowledge hit 应用到最终穿搭建议

这一层不是通用问答知识库，而是穿搭领域知识增强层。

### 2.6 Runtime / Observability / Storage 层

这一层主要负责：

- 运行时状态保存
- 日志
- 指标
- 历史 / 收藏
- 向量缓存
- 端口 / PID / 启动辅助文件
- 公网分享链路运行信息

核心目录与文件：

- `.runtime/`
- `weatherwear/support/runtime_storage.py`
- `weatherwear/support/user_state_store.py`
- `weatherwear/support/observability.py`
- `.runtime/share-demo.json`
- `.runtime/tunnel.pid`

它的价值是把“产品能跑”和“系统可维护”拉开差距。

## 3. 运行时状态、历史与收藏

这一章要专门讲清楚，因为面试官很容易把这些东西误以为“记忆系统”。

### 3.1 当前有哪些状态

WeatherWear 当前有三类典型状态：

1. 单次请求状态
- `QueryState`
- `CoordinatorResult`
- `ExecutionRecord`

2. 前端会话状态
- 当前语言
- 视图模式
- 查询输入
- 当前结果
- 当前候选选择

3. 持久化用户状态
- 历史记录
- 收藏地点

### 3.2 历史与收藏存到哪里

后端会把历史和收藏写到本地运行时目录：

- `.runtime/state/history.json`
- `.runtime/state/favorites.json`

相关代码：

- `weatherwear/support/runtime_storage.py`
- `weatherwear/support/user_state_store.py`

前端也会把一部分轻量状态存到浏览器：

- `localStorage`
- `sessionStorage`

例如：

- locale
- view mode
- confirmation mode
- 上次结果

### 3.3 为什么这不算 Agent memory

这是一个非常重要的面试边界。

当前项目虽然有：

- history
- favorites
- 缓存
- request trace

但它没有真正意义上的：

- 长期语义记忆
- 跨会话画像沉淀
- 记忆检索后再注入 prompt
- 记忆抽取 / 记忆升级 / 记忆遗忘策略

所以更准确的说法是：

> 它有运行时状态保存和用户侧持久化，但没有独立的 Agent memory 系统。

### 3.4 哪些只是 cache / persistence

当前项目里更像工程缓存或持久化的机制包括：

- 城市解析缓存
- OpenWeather 请求缓存
- embedding health cache
- Chroma / 本地向量缓存
- history / favorites 的 JSON 存储

这些机制很有价值，但不要在面试里把它们说成：

- 长期记忆
- 会话记忆
- 认知记忆系统

## 4. 轻量 RAG 架构

这一部分是 WeatherWear 面试时最值得重点展开的技术点之一。

### 4.1 为什么说是轻量 RAG

它不是做一个通用知识问答系统，而是做一个单领域、可解释、可降级的穿搭知识增强层。

它的特点是：

- 数据规模不大
- 数据结构清晰
- 场景很聚焦
- 检索结果会被显式展示和调试
- 检索失败时有降级路径

所以更准确地说，它是：

> 面向天气穿搭场景的轻量 RAG，而不是通用企业知识库系统。

### 4.2 知识来源是什么

知识源是本地 JSONL 文件：

- `weatherwear/resources/fashion_knowledge/zh-CN.jsonl`
- `weatherwear/resources/fashion_knowledge/en-US.jsonl`

这些条目包含：

- 标签
- 适用天气条件
- 场景提示
- gender compatibility
- structured guidance

这意味着知识库不是原始长文档切块，而是结构化、可控、便于维护的领域条目。

### 4.3 检索输入是什么

检索不是只看原始 query，而是把业务上下文组装起来：

- 天气温度
- 体感温度
- 湿度
- 风速
- 天气描述
- occasion_text
- occasion_tags
- primary_scene
- gender
- locale

这比“只拿用户一句话做向量检索”更贴近真实业务。

### 4.4 规则检索怎么做

第一条腿是规则检索。

规则检索会综合考虑：

- 天气条件区间是否匹配
- 场景标签是否匹配
- 主场景是否匹配
- 标签 overlap
- 性别兼容性
- 服饰类别

规则检索的优点是：

- 可解释
- 可控
- 即使 embedding 不可用也能工作

相关逻辑：

- `weatherwear/services/fashion_knowledge.py`
- `_rule_hits`

### 4.5 向量检索怎么做

第二条腿是向量检索。

它会：

1. 组装 query text
2. 调 embedding 模型生成向量
3. 优先使用 Chroma 做检索
4. Chroma 不可用时退到本地 JSON 向量缓存

相关逻辑：

- `embed_texts`
- `_vector_hits`
- `_vector_hits_from_cache`

这说明向量检索不是“有就有、没有就坏”，而是做了兼容和降级设计。

### 4.6 Chroma / 本地向量缓存降级链

当前向量链路有明确的降级顺序：

1. embedding 正常 + Chroma 正常
   - 走 Chroma
2. embedding 正常 + Chroma 异常
   - 退本地向量缓存
3. embedding 不可用
   - 整体退回 rules only

这条链路非常适合面试里讲“系统可用性设计”。

### 4.7 rerank 与知识应用怎么做

检索不是拿到就结束，还会做 rerank。

综合考虑的信号包括：

- weather match score
- occasion match score
- semantic similarity
- garment compatibility
- constraint bonus

最终挑出 top hits，写入：

- `knowledge_hits`
- `knowledge_basis`
- `debug_sections.knowledge`

这些结果不仅会参与最终建议生成，也会在前端开发者页面中可见。

所以它的价值不只是“检出来”，而是：

- 检得出来
- 排得清楚
- 用得进去
- 看得见为什么命中

### 4.8 面试表达

我做的不是通用 RAG，而是一个面向天气穿搭场景的轻量 RAG。知识源是本地结构化 JSONL 条目，先走规则检索，再结合 embedding 做向量检索，并在 Chroma 不可用时退回本地向量缓存，embedding 不可用时进一步退回纯规则模式。最后通过 rerank 把天气信号、场景信号和语义相似度合并起来，再把命中的知识显式注入最终穿搭建议和调试页面。

## 5. MCP / 工具调用能力

### 5.1 这个项目的 MCP 能力是什么

WeatherWear 确实实现了 MCP 相关能力，但要讲清楚它的定位。

项目里有一个可选的 FastMCP 服务：

- `weatherwear/integrations/weather_mcp.py`

它提供的工具能力包括：

- `query_weather(city_name)`
- `get_weather_details(city_name)`
- `get_weather_by_coords(lat, lon, lang)`

### 5.2 它在主链路里的位置

MCP 不是主业务查询链路的必备依赖。

主链路仍然是：

- FastAPI 接口
- Coordinator 编排
- Service 直接调用

MCP 更像是一个可选扩展层，方便把天气查询能力暴露成 MCP 工具。

所以最准确的表述是：

> 项目支持可选 MCP 扩展，但主链路并不是 MCP 驱动的。

### 5.3 这里的工具调用本质是什么

这个项目内部确实有很多“工具式能力”：

- 城市解析
- 天气查询
- 场景提取
- 知识检索
- 穿搭生成

但这些能力的调度方式，本质上是代码编排，而不是 LLM 原生函数调用。

也就是说：

- 不是 OpenAI function calling
- 不是 `bind_tools()` 风格的 native tool binding
- 而是 Python coordinator 决定何时调用哪个 service

### 5.4 面试表达

WeatherWear 里有两层“工具能力”概念：一层是项目内部通过 coordinator 编排的 service 调用，另一层是由 FastMCP 暴露出来的可选天气工具接口。主链路属于 code-orchestrated tool call，而不是模型原生 function calling，MCP 是额外的协议化扩展能力，不是主链路依赖。

## 6. Planner / Workflow 设计

这一章是另一个非常适合面试展开的重点。

### 6.1 为什么要有 planner

并不是所有查询都值得先过 LLM planner。

WeatherWear 当前的策略是：

- 简单天气查询，直接 fast path
- 复杂查询，才调用 supervisor planner

这样做的好处是：

- 低成本
- 低延迟
- 普通查询更稳定
- 把 LLM 用在真正需要理解和规划的地方

### 6.2 fast path vs supervisor planner

当前 planner 有两条路：

#### fast path

适用于：

- 普通地点输入
- 已有候选确认
- 已有地图坐标
- LLM 配置不完整

这时直接给出默认 plan，不先走 LLM 规划。

#### supervisor planner

适用于：

- 查询更复杂
- 用户输入里既有天气又有穿搭又有更多自然语言意图

这时会让 LLM 输出一个 JSON 执行计划，包括：

- intent
- raw_location
- need_resolution
- steps
- fallback_policy

### 6.3 LangGraph runtime vs compat fallback

Workflow 层同时支持两种执行方式：

1. `langgraph`
2. `compat_state_graph`

如果环境里有 LangGraph：

- 使用 StateGraph 编排节点

如果没有：

- 自动退回兼容执行器

这是一个非常实用的工程策略：

- 不强依赖某个框架才能跑
- 但有框架时又能获得更标准的状态图执行结构

### 6.4 固定节点图，而不是开放式自治 Agent

当前节点图是固定的：

- planner
- resolve_city
- fetch_weather
- generate_outfit
- clarify_city
- finalize

它不是让模型无限制自己决定：

- 下一步动作是什么
- 要不要再调哪个工具
- 要不要继续想

所以 WeatherWear 的准确口径是：

> 有规划节点和条件路由的状态图工作流，不是开放式自治 Agent。

### 6.5 它和 ReAct、CoT、Reflexion 的关系

#### 和 ReAct 的关系

有相似点：

- 有 plan
- 有 step
- 有 action-like service call
- 有 trace

但没有标准 ReAct 循环：

- 没有开放式 Thought -> Action -> Observation 多轮自驱
- 没有无限工具循环

#### 和 CoT 的关系

有一定关系：

- planner prompt
- city resolver prompt
- fashion prompt

都属于 prompt engineering 和结构化 reasoning 的应用。

但项目没有把内部推理链显式暴露成长链式思维系统。

#### 和 Reflexion 的关系

没有真正实现。

当前没有：

- 失败后自我反思再试
- 反思总结写回记忆
- 自主错误恢复策略学习

### 6.6 面试表达

WeatherWear 的 workflow 不是开放式 agent loop，而是固定节点状态图。系统先决定是走 fast path 还是 supervisor planner，再按 `resolve_city -> fetch_weather -> generate_outfit -> finalize` 这条主链路执行。LangGraph 可用时走标准状态图，不可用时自动切换到兼容执行器。这样既保留了 agent 风格的任务拆解能力，又避免了开放式自治带来的不稳定性。

## 7. 多模态与交互边界

这一章要讲得非常稳。

### 7.1 当前支持的输入形态

当前主要支持两类输入：

- 文本输入
- 地图坐标输入

地图输入既可以来自：

- Leaflet / OpenStreetMap
- 可选 Baidu Map JS SDK

### 7.2 为什么这不算多模态大模型系统

虽然它支持地图交互和坐标输入，但它没有：

- 图片理解
- 语音输入
- 语音输出
- 视频理解
- 视觉大模型推理

所以准确说法应该是：

> 它是文本 + 坐标双入口的交互产品，不是多模态 LLM 系统。

### 7.3 地图能力在这个项目里的价值

地图不是装饰，而是地点确认链路的重要组成部分。

它能解决：

- 文本地点歧义
- 坐标直达
- 反向地理确认
- 候选点可视化

也就是说，地图能力增强的是 location resolution 这一层，而不是多模态推理。

### 7.4 面试表达

WeatherWear 支持文本输入和地图选点，所以交互形式上比纯聊天框更完整。但它没有接入图片、语音或视觉推理模型，因此不能把它表述成多模态大模型系统，更准确的说法是“带地图交互的单场景 LLM 产品”。

## 8. Query 的完整执行流程

`POST /api/query` 是整个系统的主编排入口。

可以把完整流程拆成 8 步。

## 步骤 1：接收请求

接口接收这些关键字段：

- `query_text`
- `selected_candidate_id`
- `confirmation_mode`
- `selected_coords`
- `gender`
- `occasion_text`
- `target_date`
- `locale`
- `client_request_id`

这一阶段的目标是：

- 生成 request id
- 判断是文本查询还是地图查询
- 记录 query started 事件

## 步骤 2：提取场景上下文

如果用户带了 `occasion_text`，系统会先提取场景标签。

主要输出：

- `occasion_tags`
- `primary_scene`
- `context_tags`

这一步非常重要，因为后续：

- 检索
- 穿搭建议

都会用到这些上下文，而不是只看天气。

## 步骤 3：planner 决定走哪条路

系统会判断：

- 是不是简单查询
- 是否已有坐标
- 是否已有候选
- LLM 是否可用

然后选择：

- fast path
- supervisor planner

如果走 planner，会产出结构化 plan。

如果不走 planner，就使用默认安全 plan。

## 步骤 4：城市解析

这一阶段由 `city_resolver.py` 负责。

典型路径包括：

- alias lookup
- LLM city resolution
- candidate validation
- direct geocoding

最后会得到三种结果之一：

- `resolved`
- `needs_clarification`
- `failed`

如果需要澄清，就会进入 clarify 分支，前端让用户选候选城市。

## 步骤 5：天气查询

一旦地点确认，系统会进入天气阶段。

主要策略是：

- 优先按经纬度查
- 必要时退回 `q` 查询
- 目标日期可走 forecast day
- OpenWeather 不可用时退 demo / degraded

这一阶段不仅会得到天气结果，还会得到：

- data_mode
- source
- forecast_mode
- timezone

这些信息后面会进入最终 view model 和 debug 面板。

## 步骤 6：知识检索

天气结果拿到后，会触发轻量 RAG。

检索会先走：

- rule hits

再尝试：

- vector hits

最后：

- rerank
- 选择 top knowledge hits

并记录：

- retrieval_mode
- vector_leg_status
- vector_leg_skipped_reason

这些信息不仅影响最终穿搭建议，也能在开发者页面里直接看到。

## 步骤 7：生成穿搭建议

穿搭生成器会把这些东西一起考虑：

- weather facts
- target date
- occasion context
- gender mode
- retrieved outfit knowledge
- dominant factors
- bottomwear guidance

如果 LLM 正常：

- 走 `langchain_llm`

如果 LLM 失败或输出语言不匹配：

- 自动退回 `rule_based_fashion`

所以它不是一个“单路生成器”，而是双路线生成。

## 步骤 8：整理 view model、回写历史和观测信息

最后，系统会：

- build result view model
- 写入 history
- 输出 execution trace
- 记录 runtime event
- 返回前端结果

前端拿到结果后：

- 更新 session state
- 刷新 history
- 支持继续候选确认或收藏

## 一句话总结 Query 流程

> WeatherWear 的 Query 主链路是：接收查询后先抽取场景上下文，再决定走 fast path 还是 planner，随后完成地点解析、天气获取、轻量 RAG 检索和穿搭生成，最后把结果整理成前端 view model，并把执行轨迹、日志和历史一起沉淀下来。

## 9. 开发者页面与可观测性

这一块是 WeatherWear 很有辨识度的工程亮点。

### 9.1 可观测性是怎么落地的

系统里有一套比较完整的运行态信号：

- `ExecutionRecord`
- runtime events
- metrics snapshot
- logs tail
- health check

也就是说，每次查询不是黑箱，而是有结构化执行轨迹。

### 9.2 前端开发者页面能看什么

开发者页面可以看：

- Trace / Timeline
- Debug sections
- Model settings
- Map settings
- System status
- Logs

这意味着当系统出问题时，可以定位：

- 是 planner 没走
- 还是城市解析歧义
- 还是天气服务异常
- 还是向量检索被跳过
- 还是 LLM 退回规则生成

### 9.3 为什么这是工程亮点

很多项目做到“能回答”就结束了，但 WeatherWear 多做了一层：

- 能看见为什么这样回答
- 能看见每一步用了多久
- 能看见哪些地方降级了
- 能直接从开发者页面验证模型、地图和系统健康

这会显著提高：

- demo 说服力
- 调试效率
- 面试时的工程可信度

### 9.4 面试表达

WeatherWear 的一个工程亮点，是我把执行链路做成了可观测系统。每一步都会沉淀成 execution trace，并在前端开发者页面里展示 timeline、retrieval summary、dependency status 和日志，这样项目不只是“调模型拿结果”，而是具备调试、解释和排障能力的工程化应用。

## 10. 工程亮点

这一章适合面试时集中输出。

### 10.1 它不是简单的 prompt demo

它有：

- 完整前后端
- 状态图编排
- 轻量 RAG
- 降级链
- 可观测性
- 配置页面
- 验证脚本
- 本机 + 公网临时分享能力

### 10.2 降级链设计很完整

典型降级链包括：

- planner 不可用 -> fast path
- LangGraph 不可用 -> compat workflow
- embedding 不可用 -> rules only
- Chroma 不可用 -> 本地向量缓存
- OpenWeather 不可用 -> demo weather
- outfit LLM 失败 -> rule based fashion

这说明项目设计不是理想条件下才成立。

### 10.3 开发者体验好

项目不只是提供用户功能，还提供：

- model config
- map config
- runtime health
- logs
- trace

并且当前还能通过：

- `scripts/share_demo.py`
- `scripts/share_demo_down.py`

把 demo 用临时 HTTPS 链接分享给别人，同时自己本机继续可用。

这让它更像一个可维护、可展示的工程产品，而不只是研究 demo。

### 10.4 验证链完整

项目里有明确的验证和维护脚本：

- `scripts/validate_project.py`
- `scripts/evaluate_retrieval.py`
- `scripts/check_fashion_knowledge.py`
- `scripts/import_fashion_knowledge.py`

这让：

- 知识库维护
- 检索回归
- 前后端构建
- 项目验收

都有统一入口。

### 10.5 中英文支持完整

它不只是翻译几句 UI 文案，而是：

- 知识库双 locale
- 穿搭生成可按 locale
- 结果展示可按 locale
- UI 可按 locale

这说明它考虑的是完整产品表现，而不是局部 demo。

## 11. 能力边界

这一节一定要讲，不然面试里很容易被追问穿帮。

### 11.1 已实现

- 单场景工作流编排
- 轻量 RAG
- LangGraph 兼容执行
- LLM + 规则双路线生成
- 可选 MCP 扩展
- 开发者可观测性
- 历史 / 收藏 / 会话状态持久化
- 中英文双 locale 支持
- 基于 Quick Tunnel 的公网临时 demo 分享

### 11.2 部分实现

- 向量检索与降级链
- planner 节点式任务拆解
- 地图增强的地点确认链路

### 11.3 未实现

- 长期记忆系统
- 真正多模态大模型
- 通用 Agent 平台
- 多 Agent 协作
- 标准 ReAct 自主循环
- Reflexion 自反思
- 原生 function calling / tool binding
- 正式生产级部署闭环

### 11.4 面试表达

我会把 WeatherWear 定位成“带 agent 风格编排的 workflow 应用”，而不会把它夸成通用 agent 平台。它实现了单场景任务拆解、轻量 RAG 和可观测执行链路，但没有长期记忆、多模态大模型、开放式 ReAct 循环或 Reflexion 机制。这样表述最稳，也最符合真实代码边界。

## 12. 面试高频问题模板

## 12.1 为什么说它不是通用 Agent，而是 workflow 应用

因为它的执行图是固定节点状态图，不是让模型开放式无限决定下一步动作。planner 只是在复杂查询时生成 JSON 计划，真正的执行顺序仍由 coordinator 和 workflow 控制，所以它更像受控编排系统，而不是通用自治 agent。

## 12.2 LangGraph 在这里起了什么作用

LangGraph 在这里不是定义业务架构，而是提供状态图运行时。项目把 `planner -> resolve_city -> fetch_weather -> generate_outfit -> finalize` 编排成图结构执行；如果 LangGraph 不可用，还能自动切到兼容执行器，所以它既用了框架优势，又保留了运行稳定性。

## 12.3 规则检索和向量检索怎么协同

规则检索负责业务可控性和可解释性，向量检索负责补语义召回。最终不是简单拼接，而是通过 rerank 把 weather match、occasion match、semantic similarity 等信号合并，得到更适合当前天气和场景的知识依据。

## 12.4 为什么要做 compat workflow fallback

因为 LangGraph 是增强能力，不应该成为系统唯一运行前提。compat workflow 让项目在依赖不完整时也能跑主链路，减少环境耦合，适合本地开发、演示和低配运行环境。

## 12.5 为什么说 history / favorites 不等于记忆系统

history 和 favorites 是用户状态持久化，不是语义记忆。它们不会被自动抽取成长久画像，也不会作为跨会话的知识记忆回注到 prompt 里，所以不能把它们说成长久记忆，只能说是 runtime persistence。

## 12.6 MCP 在这个项目里是什么定位

MCP 是可选扩展层。项目用 FastMCP 暴露了天气查询能力，但主业务查询链路仍然是 FastAPI + coordinator + services，不依赖 MCP 才能工作。

## 12.7 如果 embedding / Chroma / OpenWeather 出问题，系统如何降级

embedding 不可用时，检索退回 rules only；Chroma 不可用时退回本地向量缓存；OpenWeather 不可用时退回 demo weather；穿搭 LLM 失败时退回 rule-based fashion。也就是说关键链路都设计了退路，不会因为单点依赖失败直接整体不可用。

## 12.8 当前的公网 demo 分享能力怎么讲

当前项目支持通过 `cloudflared` 启动 Cloudflare Quick Tunnel，把本机运行的 WeatherWear 暴露成临时 HTTPS 链接，让别人通过浏览器访问 demo，同时本机自己仍然可以继续使用。这适合演示、答辩和作品集分享，但不等于正式生产托管。

## 13. 接口白话说明

这一节的目标不是讲实现细节，而是讲清楚：

- 这个接口干什么
- 什么时候用
- 最关键的输入输出是什么

## 13.1 查询主链路接口

### `POST /api/query`

这是整个系统最核心的接口。

可以把它理解成：

> 把用户的地点、天气、场景相关输入交给 WeatherWear，系统会自己完成地点确认、天气查询、知识检索、穿搭建议生成，并返回结构化结果页面数据。

关键输入包括：

- `query_text`
- `selected_coords`
- `selected_candidate_id`
- `confirmation_mode`
- `gender`
- `occasion_text`
- `target_date`
- `locale`

关键输出包括：

- `ok`
- `view_model`

其中 `view_model` 里已经包含：

- hero summary
- weather
- fashion
- clarification options
- timeline steps
- knowledge basis
- debug sections

### `POST /api/query/cancel`

这个接口是取消当前查询的。

可以理解成：

> 当前这次查询不要继续跑了，终止后端正在执行的流程。

适合：

- 用户主动取消
- 查询过慢
- 前端切换操作时中断旧请求

## 13.2 健康检查与示例接口

### `GET /api/health/runtime`

这个接口用于查看当前运行状态。

它会返回：

- 依赖健康情况
- 配置状态
- 运行模式

适合：

- 启动后检查系统能不能正常工作
- 开发者页面展示当前环境状态

### `GET /api/examples`

这个接口返回示例查询。

适合：

- 前端默认示例展示
- 新用户快速体验

## 13.3 模型配置接口

### `GET /api/settings/model`

读取当前模型配置。

可以看：

- chat provider
- embedding provider
- 是否配置完整
- 当前 embedding 健康状态

### `PUT /api/settings/model`

更新模型配置。

适合：

- 修改 base URL
- 修改 model
- 更新 API Key
- 切换默认 provider

### `POST /api/settings/model/test`

测试模型连接。

作用是：

> 不真正跑完整查询，只验证 chat model 或 embedding model 当前能不能连通。

## 13.4 地图配置接口

### `GET /api/settings/map`

读取当前地图配置。

### `PUT /api/settings/map`

更新地图配置。

### `POST /api/settings/map/test`

测试地图配置是否可用。

适合：

- 切换地图 provider
- 检查 Baidu Map 配置
- 检查默认地图模式是否正常

## 13.5 历史与收藏接口

### `GET /api/history`

获取历史查询列表。

### `POST /api/history`

手动新增历史记录。

虽然主链路通常会自动写历史，但这个接口也保留了手动写入能力。

### `DELETE /api/history/{item_id}`

删除一条历史记录。

### `GET /api/favorites`

获取收藏地点列表。

### `POST /api/favorites`

新增收藏地点。

### `DELETE /api/favorites/{item_id}`

删除收藏地点。

## 13.6 日志与开发者接口

### `POST /api/logs/client-event`

前端把运行时事件回传给后端日志系统。

### `GET /api/logs/sources`

查看可读的日志源列表。

### `GET /api/logs/tail`

查看某个日志源的尾部内容。

适合：

- 开发者排障
- 前端开发者页面展示日志 tail

### `GET /api/dev/session`

查看当前开发者会话状态。

### `POST /api/dev/unlock`

用 PIN 解锁开发者模式。

### `POST /api/dev/lock`

锁回开发者模式。

## 13.7 最后怎么理解这些接口的关系

可以一句话这样理解：

- `/api/query` 负责真实业务主链路
- `/api/settings/*` 负责配置与能力验证
- `/api/history`、`/api/favorites` 负责用户状态持久化
- `/api/logs/*`、`/api/health/runtime` 负责运行态可观测性
- `/api/dev/*` 负责开发者页面访问控制

另外，当前代码还具备：

- `/` 提供前端页面
- `/assets/*` 提供前端静态资源
- `scripts/share_demo.py` 启动公网临时分享
- `scripts/share_demo_down.py` 关闭分享

所以整个 WeatherWear 不是只有一个“查询接口”，而是已经形成了：

- 业务入口
- 配置入口
- 调试入口
- 状态入口
- 分享入口

这几类能力共同组成的完整应用系统。

## 14. 最后 30 秒总结

如果面试官只给 30 秒，可以这样说：

> WeatherWear 是一个面向天气穿搭场景的 LLM 应用工程项目。它是用 coordinator + 状态图 workflow 把地点解析、天气查询、轻量 RAG 和穿搭建议生成串起来，同时做了完整的降级链、开发者可观测页面，以及本机到公网临时 demo 分享能力。它的亮点在于 workflow 编排、可解释检索、运行稳定性和工程完整度。

## 15. 最后 3 分钟总结

如果面试官愿意听 3 分钟，可以这样组织：

1. 先讲定位  
这是一个单场景 LLM 工作流产品，目标是把天气穿搭这件事做成完整工程。

2. 再讲主链路  
用户输入文本或地图坐标后，系统会先做场景上下文提取，再决定 fast path 还是 supervisor planner，然后完成城市解析、天气获取、轻量 RAG、穿搭生成和结果 view model 组装。

3. 再讲技术亮点  
核心亮点是轻量 RAG、LangGraph 兼容执行、完整降级链、开发者可观测性，以及现在支持本机 + Cloudflare Quick Tunnel 的临时公网 demo 分享。embedding、Chroma、OpenWeather、LLM 任意一层出问题，系统都尽量退到还能工作的路径。

4. 最后讲边界  
它没有长期记忆、没有真正多模态大模型、没有开放式 ReAct 或 Reflexion，所以我会把它定位成“有 agent 风格编排的 workflow 应用”，而不是通用自治 Agent。
