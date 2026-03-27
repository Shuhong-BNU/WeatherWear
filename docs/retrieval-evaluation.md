# 检索评测说明

## 目标

这套评测不是做通用 Benchmark，而是做一个**离线、轻量、可重复运行**的回归检查。

它主要回答三个问题：

- 当前 query 是否能命中合理知识条目
- 当前降级路径是否符合预期
- 当前检索改动有没有把原来正确的结果打坏

## 入口

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --cases weatherwear/resources/evaluation/retrieval_cases.sample.json `
  --pretty `
  --fail-on-check
```

如需写出 JSON 结果：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --cases weatherwear/resources/evaluation/retrieval_cases.sample.json `
  --output .runtime/retrieval-eval.json
```

## case 结构

每个 case 至少包含：

- `name`
- `locale`
- `weather`
- `query_context`

可选 expectation 字段：

- `expected_any_hit_ids`
- `expected_top_hit_ids`
- `expected_retrieval_mode`
- `expected_vector_leg_status`

仓库内的 `weatherwear/resources/evaluation/retrieval_cases.sample.json` 已包含一组 `en-US` / `zh-CN` 对齐 case，可直接用于双 locale 回归检查。
当前示例 expectation 默认按“未配置 embedding 的本地开发环境”写成 `rules_only + skipped`；如果你启用了向量检索，请按当前配置调整 expectation。

## expectation 含义

- `expected_any_hit_ids`
  - 只要求“这些 id 至少命中一个或多个”
  - 适合结果允许轻微排序波动的场景
- `expected_top_hit_ids`
  - 要求 top hit 前缀严格一致
  - 适合你非常确定排序应稳定的 case
- `expected_retrieval_mode`
  - 检查当前是 `rules_only` 还是混合检索
- `expected_vector_leg_status`
  - 检查向量腿是否正常运行、跳过或降级

## 什么时候算 regression

以下任一情况都应视为回归候选：

- 原本应命中的知识条目完全不再命中
- 降级链路改变且与当前配置不符
- 排名大幅偏移，导致 top 结果失去业务合理性
- 新增知识条目后，旧 case 大面积失败

## 扩充建议

优先补这几类 case：

- 冷天通勤
- 雨天步行 / 周末外出
- 炎热天气约会 / 轻出行
- 中英双 locale 对齐 case

不建议把它扩成复杂评测平台；当前价值重点是：

- 可维护
- 可解释
- 能做回归守门
