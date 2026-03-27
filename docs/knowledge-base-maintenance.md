# 知识库维护说明

## 目标

本项目的知识库维护重点不是“平台化 ingestion”，而是：

- 条目格式正确
- 词表和 locale 一致
- 索引可重建
- 检索效果可回归验证

## 推荐维护顺序

### 1. 先做导入预检

```powershell
.\.venv\Scripts\python.exe scripts/import_fashion_knowledge.py `
  --input weatherwear/resources/examples/fashion_knowledge_import.sample.json `
  --locale en-US `
  --validate-only
```

这一步主要检查：

- 必填字段
- category 合法性
- tags / occasion_hints / gender_compatibility 规范化
- `weather_conditions` / `structured_guidance` 结构正确性
- 重复 id / 重复签名 / 异常词表

### 2. 再做全库校验

```powershell
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py
```

这一步会补充检查：

- 中英 locale 的 id 对齐
- category 对齐
- 全库统计摘要

### 3. 必要时重建索引

```powershell
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py --rebuild-index
```

如果需要强制清缓存再重建：

```powershell
.\.venv\Scripts\python.exe scripts/check_fashion_knowledge.py --rebuild-index --force
```

### 4. 最后做检索回归验证

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py `
  --cases weatherwear/resources/evaluation/retrieval_cases.sample.json `
  --pretty `
  --fail-on-check
```

## 什么时候需要重建索引

建议在以下情况后重建：

- 新增或删除知识条目
- 修改了大量 summary / body / tags
- 修改了 embedding 配置
- 怀疑 Chroma / 本地向量缓存与当前知识库不同步

## 不建议做的事

当前项目不建议为了“包装能力”去做：

- 通用 chunking 平台
- 自动切片平台
- 在线 feedback loop
- 通用 Agent 知识库

当前最有价值的是把现有维护链路保持成：

- 可解释
- 可验证
- 能稳定服务当前业务域
