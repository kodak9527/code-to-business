---
name: code-to-business
description: Use when the user wants to understand Java code in plain business terms -- also works as a standalone CLI or OpenCode tool. Reads all Java source files, uses an internal LLM (OpenAI-compatible API) to explain business logic, and generates a self-contained HTML document with Mermaid sequence/flow diagrams. For e-commerce ops beginners who can read code repos but don't know Java.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [java, business-analysis, documentation, html, mermaid, e-commerce]
    related_skills: [architecture-diagram, hermes-agent-skill-authoring]
---

# Java → 业务文档生成器

## 概述

一个完整的 pipeline，把 Java 代码仓翻译成小白能看懂的 HTML 业务文档，附带时序图和流程图。

**核心流程：**
1. 收集 Java 文件，按功能簇分组（Controller + Service + Mapper + DTO）
2. 每个功能簇发给公司内部 LLM，LLM 用中文解释业务逻辑
3. 汇总结果，自动生成 Mermaid 时序图/流程图
4. 组装成一个自包含的 HTML 文件，浏览器打开即看

**安全红线：** 所有代码只能在公司内网流转。LLM API 地址必须指向公司内部地址，不能是公网服务。

## 何时使用

- 「帮我分析一下这个 Java 项目的业务逻辑」
- 「下单接口的完整链路是什么样的」
- 「这个模块有哪些接口，每个接口做什么」
- 「把这批代码翻译成运营能看懂的文档」

**不要用于：**
- 代码审查/性能分析（这不是该 skill 的目的）
- 非 Java 项目

## 前置配置

使用前必须配置内部 LLM 的连接信息：

```bash
# 创建配置文件
cp ~/.hermes/skills/devops/java-to-business-doc/config.example.yaml \
   ~/.hermes/skills/devops/java-to-business-doc/config.yaml

# 编辑配置
vim ~/.hermes/skills/devops/java-to-business-doc/config.yaml
```

配置内容：
```yaml
llm:
  base_url: "http://your-internal-llm.company.com/v1"
  api_key: "your-api-key"
  model: "your-model-name"
  max_tokens: 4096
  temperature: 0.3
```

**警告：** base_url 必须是公司内网地址。不要填写任何公网 LLM 地址。

## 两种使用模式

### 模式 A: 单接口深度分析

深入分析一个接口的完整业务链路。

```
用户: "分析 OrderController 的 createOrder 方法"
```

输出：该接口的完整业务文档，包括每一步的调用时序、业务规则、异常处理。

### 模式 B: 模块全景扫描

扫描整个模块/包下所有接口，生成目录式文档。

```
用户: "分析 order 包下所有代码"
```

输出：每个接口都有独立章节，侧边栏导航，可搜索。

## 工作流

### Step 1: 确认目标

让用户明确要分析的范围：

- 单个 Controller 文件 → 模式 A
- 一个包/模块 → 模式 B
- 多个文件 → 模式 B

### Step 2: 配置检查

读取 `config.yaml`，确认 LLM 连接信息已填写。如果未配置，引导用户完成配置。

### Step 3: 收集分组

```bash
python3 scripts/collector.py \
  --target <目标目录或文件> \
  --mode deep|overview \
  --output /tmp/jbd/file_groups.json
```

`--mode deep`：对每个 Controller 方法单独建一个功能簇，包含它调用链上所有代码。
`--mode overview`：按 Controller 分组，每个 Controller 一个功能簇，包含该 Controller 的所有方法和相关代码。

### Step 4: LLM 分析

```bash
# 不带校验（快）
python3 scripts/llm_analyzer.py \
  --groups /tmp/jbd/file_groups.json \
  --config config.yaml \
  --output /tmp/jbd/analysis_results.jsonl

# 带自动二次校验（推荐，慢但准）
python3 scripts/llm_analyzer.py \
  --groups /tmp/jbd/file_groups.json \
  --config config.yaml \
  --output /tmp/jbd/analysis_results.jsonl \
  --verify
```

此脚本会：
1. 读取每个功能簇包含的 Java 文件内容
2. 组装结构化 Prompt（见 `references/prompt_template.md`）
3. 调用内部 LLM API
4. 将 LLM 的 6 部分结构化输出保存为 JSONL

**--verify 模式**（推荐）：分析完成后自动进入二次校验——把原始代码 + LLM 第一次的分析结果一起发回去，让它自己挑错。校验通过的打绿标，有修正的在 HTML 中标注为可展开的修正卡片。

**容错：** 单个簇失败不影响其他簇。失败的簇在最终 HTML 中标记为「分析失败，请手动补充」。

### Step 5: 汇总生成

```bash
python3 scripts/aggregator.py \
  --results /tmp/jbd/analysis_results.jsonl \
  --output /tmp/jbd/final_model.json
```

将 LLM 分析结果合并为统一的数据模型，生成 Mermaid 图表代码。

### Step 6: HTML 组装

```bash
python3 scripts/html_assembler.py \
  --model /tmp/jbd/final_model.json \
  --output <项目名>_业务文档.html
```

生成最终的自包含 HTML 文件（Mermaid 通过 CDN 加载）。

### Step 7: 交付

把 HTML 文件路径告诉用户。用户在浏览器打开即可查看。

## LLM Prompt 设计

详见 `references/prompt_template.md`。

核心要点：
- 要求 LLM 从「用户视角」描述业务，而不是复述代码
- 输出固定在 6 个部分（业务概述、业务流程、关键规则、调用时序、数据模型、异常情况）
- 结构化输出便于后续解析和 HTML 组装

## 输出 HTML 结构

- 顶部：项目名 + 生成时间
- 侧边栏：导航菜单（按模块/接口分组）
- 主内容区：
  - 每个接口一个独立章节
  - 业务概述（大白话，100-200字）
  - 调用时序图（Mermaid sequenceDiagram）
  - 业务流程图（Mermaid flowchart，如有分支逻辑）
  - 分步业务流程
  - 关键业务规则
  - 异常/边界情况说明
  - 数据模型速查

## 常见问题

### LLM 分析结果不准确怎么办？

1. **开启二次校验：** 使用 `--verify` 参数，LLM 会自己检查自己的分析结果，挑出错误并修正。HTML 中修正内容会以黄色卡片展示。
2. **手动编辑：** 打开 HTML，找到对应接口，手动编辑描述文字。HTML 是普通的文本内容，不需要重新生成。

### 跨模块的调用链断了？

如果 A 模块的 Controller 调用了 B 模块的 Service，而 B 模块不在扫描范围内，该调用会被标注为「外部服务调用」。要追踪完整链路，需要同时扫描 A 和 B。

### CDN 在公司内网无法访问？

Mermaid.js 默认从 jsdelivr CDN 加载。如果内网无法访问，可以：
1. 提前下载 mermaid.min.js 放到 HTML 同目录
2. HTML 会自动检测 CDN 失败并提示用户

## 验证清单

- [ ] config.yaml 已配置内部 LLM 地址和密钥
- [ ] 目标 Java 项目路径存在
- [ ] collector.py 能正常识别 Controller/Service/Mapper
- [ ] LLM 返回的 6 部分结构完整
- [ ] 生成的 HTML 中 Mermaid 图表正常渲染
- [ ] 所有接口都在导航栏中有入口
