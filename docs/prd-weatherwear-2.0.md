# WeatherWear PRD

## 1. 文档信息

- 产品名称：WeatherWear
- 文档版本：v2.0
- 文档日期：2026-04-04
- 文档状态：当前代码对齐版
- 文档用途：
  - 统一产品定位
  - 统一技术边界
  - 为演示、答辩、面试、后续迭代提供正式说明

## 2. 项目概述

WeatherWear 是一个围绕“地点确认 -> 天气查询 -> 穿搭建议 -> 可观测执行链路”构建的 LLM 应用项目。

它的核心目标不是做通用 Agent 平台，而是把天气穿搭这一单场景任务做成一个具备：

- 前后端完整体验
- 工作流编排
- 轻量 RAG
- 降级链
- 开发者可观测性
- 公网临时 demo 分享能力

的工程化系统。

当前系统既面向普通使用者，也面向项目演示和技术评审场景。

## 3. 项目目标

### 3.1 产品目标

1. 让用户可以通过文本或地图选点快速完成天气穿搭查询。
2. 让系统不仅“能给建议”，还“能解释建议怎么来的”。
3. 让项目具备完整演示能力，包括本机使用和公网临时分享。
4. 为后续升级到更正式的线上部署保留清晰的工程基础。

### 3.2 技术目标

1. 用 workflow 编排替代“单次 prompt 黑盒调用”。
2. 用轻量 RAG 为穿搭建议提供领域知识增强。
3. 为关键依赖设计 fallback，提升系统可用性。
4. 用 trace、日志、健康检查和配置页面提高调试效率。

### 3.3 非目标

当前版本不以这些为目标：

- 通用 Agent 平台化
- 多 Agent 协作
- 长期记忆系统
- 真正多模态大模型
- 正式生产级部署闭环

## 4. 业务背景

天气查询和穿搭建议本身是一个高频、轻决策场景，适合做成结构清晰、反馈即时的 LLM 应用。

如果只是简单接一个模型 API，通常会有几个问题：

1. 地点歧义不好处理
2. 天气事实和建议逻辑容易混在一起
3. 结果不可解释
4. 外部依赖出错时系统容易直接不可用
5. 面试或演示时很难说明项目工程价值

WeatherWear 的设计重点，就是把这些问题做成一个结构明确、可观察、可降级的工程化解法。

## 5. 产品定位

WeatherWear 的定位是：

> 一个面向天气穿搭场景的、带工作流编排和轻量 RAG 的 LLM 应用工程。

它不是：

- 通用 Agent 平台
- 多智能体协作系统
- 记忆驱动型个性化平台
- 多模态视觉 / 语音系统

它更适合被定位为：

- 单场景 AI 产品
- 可展示的工程项目
- 可解释的 workflow 应用

## 6. 用户角色

### 6.1 主要用户

1. 普通终端用户
   - 想查某地天气
   - 想获得对应穿搭建议
   - 可能更喜欢文本输入，也可能更喜欢地图选点

2. 项目演示对象
   - 面试官
   - 老师
   - 同学
   - 同事
   - 作品集访问者

### 6.2 次要用户

1. 开发者本人
   - 调试模型、地图、日志、trace

2. 技术评审者
   - 关注架构分层
   - 关注 AI 工程能力
   - 关注系统边界

## 7. 使用场景

1. 用户直接输入地点查询天气和穿搭建议
2. 用户使用地图选点查询天气和穿搭建议
3. 用户输入歧义地点，由系统给出候选确认
4. 用户附带场景信息，例如通勤、约会、出游、开会
5. 开发者通过调试页面查看执行链路、日志和依赖状态
6. 项目作者通过临时公网链接向外部展示 demo

## 8. 范围定义

### 8.1 当前已实现

1. 单场景工作流编排
2. 文本查询和地图选点
3. 城市候选确认
4. OpenWeather 查询
5. 轻量 RAG
6. 穿搭建议生成
7. 历史记录与收藏地点
8. 开发者页面
9. 中英文切换
10. FastAPI 托管 `frontend/dist`
11. 基于 Cloudflare Quick Tunnel 的 demo 分享

### 8.2 当前部分实现

1. 向量检索与降级链
2. LangGraph 兼容执行
3. planner 节点式任务拆解
4. MCP 可选扩展

### 8.3 当前明确不做

1. 长期记忆系统
2. 多模态视觉 / 语音大模型
3. 通用 Agent 平台
4. 多 Agent 协作
5. 标准 ReAct / Reflexion
6. 正式生产上线闭环

## 9. 成功指标

### 9.1 产品指标

1. 用户可以完成一次完整的地点确认、天气查询和穿搭建议获取
2. 系统在地点歧义时能够给出候选项，而不是直接失败
3. 用户可以通过界面查看历史和收藏
4. 用户能够在浏览器中完成从输入到结果展示的完整流程

### 9.2 工程指标

1. 主链路执行可被 trace
2. 检索模式和降级路径可被观察
3. 依赖健康状态可被查看
4. 模型和地图配置可被测试

### 9.3 演示指标

1. 本机可稳定运行应用
2. 外部访问者可通过临时 HTTPS 链接打开 demo
3. 演示期间本机使用和公网访问可以共存

## 10. 产品原则

1. 单场景聚焦  
优先把天气穿搭这件事做完整，而不是做大而全平台。

2. 可解释优先  
不仅给结果，也要能解释主链路和知识依据。

3. 可用性优先  
关键依赖必须尽量有 fallback。

4. 工程透明优先  
调试、观测、配置和验证能力要清晰暴露。

5. 边界清晰  
不夸大成长期记忆、多模态、自治 Agent 或正式生产系统。

## 11. 功能架构

产品功能可拆成以下模块：

1. 查询输入模块
2. 地点确认模块
3. 天气查询模块
4. 穿搭生成模块
5. 轻量 RAG 模块
6. 历史 / 收藏模块
7. 开发者控制台模块
8. Demo 分享模块

## 12. 详细功能需求

### 12.1 查询输入模块

#### 功能描述

支持用户通过文本输入地点或通过地图选点发起天气穿搭查询。

#### 输入

- `query_text`
- `selected_coords`
- `occasion_text`
- `target_date`
- `gender`
- `locale`

#### 功能点

1. 文本查询
2. 地图选点查询
3. 日期输入
4. 场景输入
5. 示例输入

#### 业务规则

1. 无文本但有坐标时，系统仍可继续主链路
2. 查询应支持 locale 透传
3. 当前请求应支持取消

### 12.2 地点确认模块

#### 功能描述

将用户的地点表达解析为可用于天气查询的明确城市或坐标。

#### 功能点

1. alias lookup
2. LLM city resolution
3. direct geocoding
4. candidate validation
5. clarification

#### 业务规则

1. 地点明确时直接进入天气查询
2. 地点歧义时必须给出候选项
3. 地图选点时优先按坐标链路处理

### 12.3 天气查询模块

#### 功能描述

在地点明确后，根据城市或坐标查询当前或目标日期天气。

#### 功能点

1. 当前天气查询
2. 目标日期天气查询
3. 坐标优先查询
4. `q` 查询 fallback
5. demo / degraded fallback

#### 业务规则

1. 坐标可用时优先走坐标路径
2. OpenWeather 失败时应根据 fallback 策略尽量降级
3. 天气结果应保留足够结构化字段供后续生成使用

### 12.4 穿搭生成模块

#### 功能描述

根据天气事实、场景上下文和知识命中结果生成穿搭建议。

#### 功能点

1. LLM 生成
2. 规则生成 fallback
3. locale-aware 输出

#### 业务规则

1. 没有有效天气结果时不应硬生成完整建议
2. LLM 失败时应自动退回规则建议
3. 建议应尽量与 locale 一致

### 12.5 轻量 RAG 模块

#### 功能描述

使用本地穿搭知识库为穿搭建议提供领域增强。

#### 知识源

- `weatherwear/resources/fashion_knowledge/zh-CN.jsonl`
- `weatherwear/resources/fashion_knowledge/en-US.jsonl`

#### 功能点

1. 规则检索
2. 向量检索
3. Chroma 检索
4. 本地向量缓存 fallback
5. rerank

#### 业务规则

1. 检索输入应综合天气、场景、性别和 locale
2. Chroma 不可用时应尝试本地缓存
3. Embedding 不可用时应退回规则模式
4. 检索结果应能暴露到调试页面

### 12.6 历史 / 收藏模块

#### 功能描述

保存查询历史和收藏地点。

#### 当前存储方式

- `.runtime/state/history.json`
- `.runtime/state/favorites.json`

#### 功能点

1. 查询完成后自动写历史
2. 查看历史
3. 查看收藏
4. 新增收藏
5. 删除历史 / 收藏

#### 边界说明

这部分属于状态持久化，不等于长期记忆系统。

### 12.7 开发者控制台模块

#### 功能描述

为开发者提供系统状态、日志、trace、模型设置和地图设置等能力。

#### 功能点

1. Developer session
2. Model settings
3. Map settings
4. Runtime health
5. Logs
6. Trace / Timeline / Debug sections

#### 业务规则

1. 开发者入口需要显式解锁
2. 配置读取与测试应与普通用户入口隔离
3. 运行日志应可读可追踪

### 12.8 Demo 分享模块

#### 功能描述

在不租服务器的前提下，把本机运行的 WeatherWear 临时分享给外部访问者。

#### 当前实现

- `scripts/share_demo.py`
- `scripts/share_demo_down.py`
- `.runtime/share-demo.json`
- `.runtime/tunnel.pid`
- `.runtime/logs/tunnel.log`

#### 业务规则

1. 本机启动应用后可再启动分享链路
2. 分享链接应为 HTTPS
3. 停止分享时可只关闭 tunnel，不必强制关闭本机应用
4. 该能力只面向 testing / development / quick demo，不作为正式生产托管方案

## 13. 核心用户流程

### 13.1 文本查询流程

1. 用户输入地点和场景描述
2. 系统解析场景和地点
3. 系统查询天气
4. 系统检索知识
5. 系统生成穿搭建议
6. 页面展示结果

### 13.2 地图选点流程

1. 用户在地图上选择位置
2. 系统获取坐标
3. 系统优先按坐标解析地点与天气
4. 系统生成结果

### 13.3 歧义地点流程

1. 用户输入歧义地点
2. 系统返回候选城市
3. 用户确认候选项
4. 系统继续天气与穿搭链路

### 13.4 开发者调试流程

1. 开发者解锁会话
2. 查看模型配置、地图配置、健康状态
3. 发起查询
4. 在 trace / logs / debug 页面定位问题

### 13.5 公网 demo 分享流程

1. 本机启动 WeatherWear
2. 执行 `scripts/share_demo.py`
3. 脚本启动 Quick Tunnel
4. 复制分享链接给外部访问者
5. 外部访问者通过浏览器访问 demo

## 14. 页面与交互要求

### 14.1 查询页

应支持：

- 文本输入
- 日期输入
- 场景输入
- 地图选点入口
- 示例查询入口

### 14.2 结果页

应展示：

- 位置结果
- 天气结果
- 穿搭建议
- 需要时的候选确认
- 适量的解释信息

### 14.3 历史 / 收藏页

应支持：

- 查看历史记录
- 查看收藏地点
- 删除历史 / 收藏

### 14.4 开发者页

应支持：

- 查看系统状态
- 查看模型与地图配置
- 查看日志
- 查看执行 trace

## 15. 数据需求

### 15.1 主要数据对象

1. Query request / response
2. City resolution result
3. Weather result
4. Fashion result
5. Retrieval result
6. Execution trace
7. History item
8. Favorite item
9. Runtime event
10. Share demo info

### 15.2 当前数据落点

- `.runtime/state/history.json`
- `.runtime/state/favorites.json`
- `.runtime/logs/*`
- `.runtime/share-demo.json`
- `.runtime/tunnel.pid`
- `.runtime/chroma/*`

### 15.3 数据处理边界

1. 历史和收藏不是数据库存储，而是本地 JSON
2. 当前不存在多用户隔离
3. 当前不存在真正的长期记忆存储

## 16. 技术方案

### 16.1 技术架构分层

1. 前端交互层
   - React 18
   - TypeScript
   - React Router
   - React Query
   - Leaflet / 可选 Baidu Map

2. API 层
   - FastAPI
   - Pydantic
   - Uvicorn

3. 编排层
   - Coordinator
   - Workflow
   - LangGraph / compat fallback

4. 业务能力层
   - city_resolver
   - weather_service
   - occasion_parser
   - fashion_agent
   - presentation

5. 检索层
   - 本地 JSONL 知识库
   - Embedding
   - Chroma
   - 本地向量缓存

6. 运行支撑层
   - runtime storage
   - user state store
   - logs / events / metrics
   - share demo runtime files

### 16.2 核心技术组件

#### 前端

- React 18
- TypeScript
- Vite
- React Router DOM
- @tanstack/react-query
- i18next
- Tailwind CSS

#### 后端

- FastAPI
- Pydantic v2
- Uvicorn
- requests
- python-dotenv

#### AI / 检索

- LangChain
- LangGraph
- OpenAI-compatible Chat / Embedding Provider
- JSONL 知识库
- Chroma

#### 可选扩展

- FastMCP
- Baidu Map JS SDK

### 16.3 主执行链路

```text
/api/query
  -> coordinator.process_query
  -> planner
  -> resolve_city
  -> fetch_weather
  -> retrieve_knowledge
  -> generate_outfit
  -> presentation.build_result_view_model
  -> frontend state / result UI
```

### 16.4 降级链设计

1. planner 不可用 -> fast path
2. LangGraph 不可用 -> compat workflow
3. embedding 不可用 -> rules only
4. Chroma 不可用 -> 本地向量缓存
5. OpenWeather 不可用 -> demo weather
6. outfit LLM 失败 -> rule-based fashion

### 16.5 Demo 分享技术路径

1. 本机运行 FastAPI
2. `frontend/dist` 存在时由 FastAPI 直接托管前端
3. 使用 `cloudflared` 启动 Cloudflare Quick Tunnel
4. 输出临时 HTTPS 链接

### 16.6 关于 cloudflared 的说明

`cloudflared` 是 Cloudflare Tunnel 的本地客户端，用来把本地服务暴露到 Cloudflare 网络。

参考：

- [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/)
- [Quick Tunnels / TryCloudflare](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)
- [Cloudflare Tunnel Setup](https://developers.cloudflare.com/tunnel/setup/)

按当前 Quick Tunnel 的使用方式，这条 demo 分享链路本身不会自动开始收费，但它只适合 testing / development / quick demo，不适合 production。

## 17. 接口与对外能力

### 17.1 业务接口

- `POST /api/query`
- `POST /api/query/cancel`

### 17.2 配置接口

- `GET /api/settings/model`
- `PUT /api/settings/model`
- `POST /api/settings/model/test`
- `GET /api/settings/map`
- `PUT /api/settings/map`
- `POST /api/settings/map/test`

### 17.3 状态接口

- `GET /api/health/runtime`
- `GET /api/history`
- `POST /api/history`
- `DELETE /api/history/{item_id}`
- `GET /api/favorites`
- `POST /api/favorites`
- `DELETE /api/favorites/{item_id}`

### 17.4 调试接口

- `GET /api/logs/sources`
- `GET /api/logs/tail`
- `GET /api/dev/session`
- `POST /api/dev/unlock`
- `POST /api/dev/lock`

### 17.5 现有外部可用能力

- `/` 返回前端页面
- `/assets/*` 返回前端静态资源
- `scripts/share_demo.py` 启动 Quick Tunnel 公网分享
- `scripts/share_demo_down.py` 停止公网分享

## 18. 风险与边界

### 18.1 产品边界

1. 不是通用 Agent 平台
2. 没有长期记忆系统
3. 没有真正多模态能力
4. 没有标准 ReAct / Reflexion
5. 不等于正式生产系统

### 18.2 工程风险

1. CORS 仍偏开发态
   - 当前配置为 `allow_origins=["*"]` + `allow_credentials=True`

2. 状态持久化仍偏 demo 态
   - history / favorites 为本地 JSON

3. Windows 前端构建稳定性仍需关注
   - 当前环境里出现过 `esbuild spawn EPERM`

4. 公网分享依赖本机在线
   - 电脑关机或断网后外部访问即失效

### 18.3 风险应对方向

1. 保持 demo 与正式部署口径分离
2. 继续强化 fallback 策略
3. 后续若要正式上线，应补数据库、HTTPS、反向代理、权限与部署硬化

## 19. 非功能需求

### 19.1 可用性

1. 查询主链路应尽量具备 fallback
2. 依赖异常时系统应尽量降级，而不是整体不可用

### 19.2 可调试性

1. 执行链路应可 trace
2. 检索状态应可观察
3. 关键设置应可测试

### 19.3 可演示性

1. 本机应可启动并运行
2. demo 应能通过浏览器对外分享
3. 普通用户和开发者都应有可用入口

### 19.4 可维护性

1. 启动、关闭、校验应有脚本化入口
2. 知识库应可导入、校验、评估

## 20. 验收标准

### 20.1 主链路验收

1. 用户可以通过文本输入发起查询
2. 用户可以通过地图选点发起查询
3. 地点歧义时系统可返回候选项
4. 查询成功时系统返回天气与穿搭结果
5. 查询结束后可在历史记录中看到结果

### 20.2 开发者能力验收

1. 开发者可解锁开发者会话
2. 可以查看运行时健康状态
3. 可以查看日志源和日志 tail
4. 可以查看执行 trace / timeline / debug
5. 可以读取并测试模型与地图配置

### 20.3 RAG 验收

1. 系统可从本地 JSONL 知识库读取知识
2. 规则检索可工作
3. Embedding / Chroma 可用时可进入向量检索
4. Chroma 或 embedding 出问题时能降级

### 20.4 Demo 分享验收

1. 本机启动后可运行 `scripts/share_demo.py`
2. 生成公网 HTTPS 分享链接
3. 外部浏览器可打开 demo
4. 运行 `scripts/share_demo_down.py` 可关闭分享

## 21. 里程碑建议

### M1：当前可演示版本

目标：

- 本机稳定运行
- 主查询链路可用
- 开发者页面可演示
- 轻量 RAG 可解释
- Quick Tunnel 可分享

当前状态：

- 已达到

### M2：准上线强化版本

目标：

- 修复前端构建稳定性问题
- 区分 dev / demo / prod 配置
- 收紧 CORS
- 优化会话与权限控制
- 明确 demo 与正式部署边界

当前状态：

- 建议下一阶段推进

### M3：正式部署版本

目标：

- 反向代理
- HTTPS
- 环境变量管理
- 数据库替代 JSON 状态文件
- 更完整的权限与运维方案

当前状态：

- 尚未实现

### M4：产品化增强版本

目标：

- 多用户隔离
- 更正式的收藏 / 历史管理
- 更强的检索评估和回归体系
- 更完善的对外展示与运维能力

当前状态：

- 未来方向，不属于当前代码事实

## 22. 总结

WeatherWear 当前最准确的产品定义是：

> 一个面向天气穿搭场景的、具备工作流编排、轻量 RAG、可观测执行链路和公网 demo 分享能力的 LLM 应用工程。

它已经具备完整演示价值、工程表达价值和面试表达价值，但当前仍应被视为：

- 可运行
- 可展示
- 可分享
- 可调试

而不是：

- 通用 Agent 平台
- 长期记忆系统
- 真正多模态系统
- 正式生产上线完成体
