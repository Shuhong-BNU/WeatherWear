# WeatherWear：更适合汇报与接手的新图谱说明

这份文档面向两类读者：

- 刚接手项目、想快速理解系统主链路的开发者
- 需要做汇报、培训或方案讲解的产品 / 技术同学

本轮图谱重构坚持两条原则：

- **旧版全部保留**：历史图源、旧版 PNG / SVG 都不删除、不覆盖。
- **新版只做减法**：降低信息密度，突出主链，不让三种图画成同一种图。

## 1. 本轮新增内容

- 一份逐张评审文档：`docs/weatherwear-architecture/diagram-review.md`
- 四张新版图源：
  - `docs/diagrams/architecture-layered-v3.mmd`
  - `docs/diagrams/module-relationship-v2.mmd`
  - `docs/diagrams/request-sequence-v3.mmd`
  - `docs/diagrams/data-flow-v3.mmd`
- 四张新版成品：
  - `docs/assets/diagrams/architecture-layered-v3.svg`
  - `docs/assets/diagrams/module-relationship-v2.svg`
  - `docs/assets/diagrams/request-sequence-v3.svg`
  - `docs/assets/diagrams/data-flow-v3.svg`
  - 以及对应 PNG 文件

## 2. 四张新版图分别回答什么问题

### 2.1 技术架构图

![WeatherWear 技术架构图（V3）](../assets/diagrams/architecture-layered-v3.svg)

- 适合 first look
- 重点回答“系统分几层、主链怎么串”
- 主链固定围绕：前端 → API → Coordinator / workflow → 服务组 → 资源 / 运行时

### 2.2 模块关系图

![WeatherWear 模块关系图（V2）](../assets/diagrams/module-relationship-v2.svg)

- 适合工程接手
- 重点回答“关键代码模块依赖谁、结果写到哪里”
- 保留文件名级别的关键模块，但压缩了支线数量

### 2.3 请求时序图

![WeatherWear 请求时序图（V3）](../assets/diagrams/request-sequence-v3.svg)

- 适合讲业务主链
- 重点回答“一次 `/api/query` 是怎么走完的”
- 把 `needs_clarification`、`规则兜底`、`demo / degraded` 都压成紧凑分支

### 2.4 数据流转过程图

![WeatherWear 数据流转过程图（V3）](../assets/diagrams/data-flow-v3.svg)

- 适合讲对象变形
- 重点回答“输入对象怎么变成 `view_model`，又如何被 UI / 调试面板 / 持久化消费”
- 外部依赖统一放入数据源池，避免和主链抢视觉中心

## 3. 为什么旧图会显得乱

从成品观感看，旧版图的核心问题并不是“事实不对”，而是“事实太多同时出现”：

- 模块关系图节点太多，跨列长箭头偏多
- 时序图泳道太多，主成功链路被分支和说明框稀释
- 数据流图把主链、数据源、消费端同时展开，中心区域过载
- 技术架构图已经接近汇报风格，但主箭头仍然过于发散

更完整的逐图点评见：`docs/weatherwear-architecture/diagram-review.md`

## 4. 相关代码锚点

新版图的命名和主链事实主要以以下文件为准：

- `weatherwear/api/server.py`
- `weatherwear/application/coordinator.py`
- `weatherwear/application/workflow.py`
- `weatherwear/application/presentation.py`
- `frontend/src/app/state/WeatherWearSession.tsx`
- `frontend/src/shared/api.ts`

## 5. 历史版本说明

旧版图仍然有价值：

- `module-relationship` 更适合深入排查具体模块
- `request-sequence` 更适合查看完整内部节点
- `data-flow` 更适合查看详细对象展开
- 各个 `v2` 版本则保留了教材风格的过渡方案

因此本轮不做替换，只做**并存新增**。
