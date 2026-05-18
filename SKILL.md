---
name: code-to-business
description: Use when the user wants to understand Java code in plain business terms. Works directly with OpenCode -- no external LLM config needed. Collector scans Java source files, OpenCode uses its own LLM to produce the 6-part business analysis, then aggregator + html_assembler generate a self-contained HTML document with Mermaid diagrams.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [java, business-analysis, documentation, html, mermaid, opencode]
    related_skills: [architecture-diagram, opencode]
---

# Java → 业务文档生成器（OpenCode 原生）

## 概述

`code-to-business` 把 Java 代码仓翻译成非技术人员也能看懂的 HTML 业务文档，带 Mermaid 时序图和流程图。

**v2.0 架构：不需要 config.yaml，不需要额外对接 LLM。** 管线变成：

```
Java 源码 ──▶ collector.py ──▶ 💬 OpenCode LLM ──▶ aggregator.py ──▶ html_assembler.py
```

你的 OpenCode 已经配好了公司内网 LLM——用它直接做分析，脚本只负责收集、合并、组装 HTML。

## 何时使用

- 「帮我分析一下这个 Java 项目的业务逻辑」
- 「下单接口的完整链路是什么样的」
- 「把这批代码翻译成运营能看懂的文档」
- 在 OpenCode 中直接说「用 code-to-business 分析 xxx」

**不要用于：** 代码审查/性能分析、非 Java 项目。

## 在 OpenCode 中的用法

Clone 到 OpenCode 工作目录后：

```
用 code-to-business 分析 /path/to/java-project，生成业务文档
```

OpenCode 自动读 `AGENTS.md`，按四步执行：
1. 跑 `collector.py` 收集分组
2. 用自己的 LLM + prompt 模板分析每个功能簇
3. 跑 `build_jsonl.py` 合并结果
4. 跑 `aggregator.py` + `html_assembler.py` 生成 HTML

## 两种分析模式

### 模式 A: 单接口深度分析

深入分析一个接口的完整业务链路。

```
用户: "分析 OrderController 的 createOrder 方法"
```

输出：该接口的完整业务文档，包含调用时序、业务规则、异常处理。

### 模式 B: 模块全景扫描

扫描整个模块/包下所有接口，生成目录式文档。

```
用户: "分析 order 包下所有代码"
```

输出：每个接口独立章节，侧边栏导航，可搜索。

## 工作流详解

### Step 1: 收集（collector.py）

```bash
python scripts/collector.py --target <目标> --mode deep --output output/file_groups.json
```

`--mode deep`：每个 Controller 方法单独一个功能簇。
`--mode overview`：按 Controller 分组。

### Step 2: LLM 分析（OpenCode）

OpenCode 读取 `output/file_groups.json` 和 `references/prompt_template.md`。

对每个功能簇：
1. 读取 cluster 元信息（http_method, http_path, entry_class 等）
2. 读取列出的 Java 源文件
3. 用 LLM + prompt 模板生成 6 部分分析
4. 保存为 `output/analyses/<cluster_id>.json`

6 部分分析：
- **业务概述** — 100-200字大白话
- **业务流程** — 分步骤描述
- **关键业务规则** — 代码中的判断逻辑
- **调用时序** — 缩进箭头格式（重要：aggregator 从中生成 Mermaid 图）
- **数据模型** — 涉及的数据结构
- **异常/边界情况** — 错误处理

### Step 3: 合并（build_jsonl.py）

```bash
python scripts/build_jsonl.py --dir output/analyses --output output/analysis_results.jsonl
```

### Step 4: 生成 HTML

```bash
python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

### Step 5: 验证（可选）

```bash
python scripts/verifier.py --input output/final_model.json
```

## LLM Prompt 设计

详见 `references/prompt_template.md`。

核心要点：
- 从「用户视角」描述业务，不复制代码
- 6 部分固定结构，便于 HTML 组装
- `call_chain` 用 `→` 箭头 + 缩进 → aggregator 自动生成 Mermaid 时序图

## 输出 HTML 结构

- 顶部：项目名 + 生成时间
- 侧边栏：导航菜单（按模块/接口分组）
- 主内容区：
  - 业务概述（大白话，100-200字）
  - 调用时序图（Mermaid sequenceDiagram）
  - 业务流程图（Mermaid flowchart）
  - 分步业务流程
  - 关键业务规则
  - 异常/边界情况说明
  - 数据模型速查

## 常见问题

### LLM 分析结果不准确？

手动编辑对应 `output/analyses/<cluster_id>.json` 文件，重新跑 step 3-4。

### 跨模块调用链断了？

只扫描了模块 A，但 A 调用了模块 B 的 Service——该调用标注为「外部服务调用」。要追踪完整链路，需同时扫描 A 和 B。

### CDN 在内网无法访问？

Mermaid.js 默认从 jsdelivr CDN 加载。如果内网不通：
1. 下载 mermaid.min.js 放到 HTML 同目录
2. HTML 自动检测 CDN 失败并提示

## 验证清单

- [ ] 目标 Java 项目路径存在
- [ ] collector.py 能正常识别 Controller/Service/Mapper
- [ ] OpenCode 为每个功能簇生成了分析 JSON
- [ ] build_jsonl.py 成功合并所有分析结果
- [ ] 生成的 HTML 中 Mermaid 图表正常渲染
- [ ] 所有接口都在导航栏中有入口
