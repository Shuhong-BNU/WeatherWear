# WeatherWear 架构概览

## 相关图示

- 结构化图示文档：`docs/architecture-diagrams.md`

## 项目定位

WeatherWear 是一个围绕“地点确认 -> 天气查询 -> 穿搭建议 -> 可观察调试链路”构建的 LLM 应用工程项目。

- 它是 **单应用工作流**
- 它包含 **轻量 RAG**
- 它使用 **代码编排式工具调用**
- 它 **不是** 通用 Agent 平台
- 它 **不是** 真正的 Multi-Agent 协作系统

## 核心链路

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

这条链路里：

- `coordinator` 负责总协调
- `city resolution` 负责地点识别、候选确认和 map pin 处理
- `weather service` 负责天气数据
- `fashion_knowledge` 负责规则检索 / 向量检索 / rerank / 降级
- `fashion_agent` 负责把天气与知识依据组织成最终建议
- `presentation` 负责把后端结果整理成前端可直接消费的 view model

## RAG 在这里的真实位置

本项目的 RAG 不是“通用知识问答系统”，而是“穿搭领域知识补强层”。

- 知识源：本地 JSONL
- 检索输入：天气数值、天气现象、场景标签、性别、locale
- 检索输出：知识依据片段与结构化 guidance
- 降级路径：
  - 优先规则检索
  - 若 embedding 可用，则补向量检索
  - 若 Chroma 不可用，回退到本地向量缓存
  - 若 embedding 不可用，回退到纯规则检索

所以它更准确的表述是：

- **轻量 RAG**
- **面向单业务域的知识增强**
- **可验证、可降级、可调试**

## Agent / Workflow 边界

项目内部确实存在“planner / coordinator / step record / tool-like service call”这些 Agent 风格元素，但边界要说清楚：

- 已实现的是：**workflow + 协调器编排**
- 不是：开放式自主迭代 Agent
- 不是：自发多工具 loop
- 不是：独立 memory / learning 系统
- 不是：真正多智能体协作平台

面试时更稳妥的说法是：

> 这是一个以工作流编排为核心、带轻量 RAG 和调试可观测能力的 LLM 应用工程项目。

## 开发者工具页的作用

前端开发者页不是“额外 Demo”，而是工程价值的一部分：

- `Trace / Timeline / Debug`：看执行链路和降级路径
- `Model Config`：看模型与 embedding 配置
- `Map Config`：看地图 provider 配置
- `System Status`：看依赖、配置和健康状态
- `Logs`：看运行日志与结构化事件

对外展示时，这一层能证明：

- 项目不只是“调一次 LLM API”
- 已经具备基本可观测性
- 能排查知识检索、模型配置和运行时问题
