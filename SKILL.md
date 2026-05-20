---
name: code-to-business
description: Transform Java code into business documentation. Use when asked to analyze Java projects, generate business docs from code, or explain Java interfaces to non-engineers. Works directly in OpenCode — run collector, use your LLM for the 6-part analysis, then assemble HTML with Mermaid diagrams.
---

# code-to-business — OpenCode Agent Instructions

You are executing the code-to-business pipeline. Follow these steps in order.

## Pipeline Flow

```
collector.py → [LLM 分析] → parse_analysis.py → aggregator.py → verifier.py → [用户确认] → html_assembler.py
```

你的任务：运行 collector，用 LLM 做 6 部分分析，然后由脚本组装 HTML。

## Step 0 — 初始设置（仅首次）

```bash
mkdir -p output/analyses
```

## Step 1 — 收集 Java 文件

```bash
python scripts/collector.py --target <PROJECT_PATH> --mode deep --output output/file_groups.json
```

- `--mode deep`：每个 Controller 方法一个簇（推荐）
- `--mode overview`：每个 Controller 类一个簇

阅读输出，了解有多少个簇待分析。

## Step 2 — LLM 分析（核心工作）

阅读 `references/prompt_template.md`，获取系统提示和用户提示模板。

对 `output/file_groups.json` 中的每个簇执行以下子步骤：

### Step 2a — 准备提示

读取簇的 Java 文件（`files[]` 列表）和元数据（`http_method`、`http_path`、`entry_class`、`entry_method`）。

按模板替换占位符：
- `{HTTP_METHOD} {PATH}` → 如 `POST /api/orders`
- `{CLASS}.{METHOD}` → 如 `OrderController.createOrder`
- `{CODE_BLOCKS}` → Java 源文件内容拼接

### Step 2b — 分析前验证（检查点 1）

调用 LLM 前，必须验证：

**元数据检查** — 必须包含全部必填字段：
- `http_method`、`http_path`、`entry_class`、`entry_method` 均存在且非空
- 任一字段缺失 → 跳过此簇，文件写入 `=== 状态: 失败 ===\n缺少必要元数据字段`

**代码检查** — 确认 Java 文件存在且可读：
- 每个 `files[]` 中的路径，确认文件存在且内容 > 10 字节
- 文件缺失 → 跳过簇，文件写入失败标记及缺失文件名

仅在验证通过后进入 Step 2c。

### Step 2c — 调用 LLM

发送系统提示 + 用户提示。期望返回 6 个部分：

1. `=== 业务概述 ===`（100-200 字大白话）
2. `=== 业务流程 ===`（编号步骤列表）
3. `=== 关键业务规则 ===`（ bullet 列表）
4. `=== 调用时序 ===`（缩进箭头链）
5. `=== 数据模型 ===`（字段说明）
6. `=== 异常/边界情况 ===`

### Step 2d — 分析后检查（检查点 2）

LLM 返回后，验证输出结构：

**6 部分检查** — 确认每个部分都存在：
- 必须包含全部 6 个 section header
- 缺失任意部分 → 记为部分失败，文件中包含标记并注明缺失的部分

**调用链格式检查** — 若 `=== 调用时序 ===` 非空，确认包含 `→` 箭头：
- 未找到 `→` → 文件中警告 call_chain 可能格式错误
- 这是软检查（非阻塞），我们对 LLM 有一定信任

**文件名检查** — 确认 `cluster_id` 与 `file_groups.json` 一致。

检查通过后进入 Step 2e；失败则写入失败标记及原因。

### Step 2e — 保存为 Markdown

将 LLM 原始输出保存到 `output/analyses/<cluster_id>.md`（不是 JSON）。

文件名必须与 `file_groups.json` 中的 `cluster_id` 匹配。

### 批量处理策略

簇数量 > 20 的项目：
- 每轮处理约 10 个簇
- 通过检查 `output/analyses/` 中的 `.md` 文件追踪已完成簇
- 持续直到全部完成

**断点续传**：若某轮中途结束，直接重新运行 Step 2 — 脚本会检查 `output/analyses/`，跳过已有 `.md` 文件的簇。

### 示例：组装提示

假设 `file_groups.json` 中有如下簇：
```json
{
  "cluster_id": "OrderController.createOrder",
  "http_method": "POST",
  "http_path": "/api/orders",
  "entry_class": "OrderController",
  "entry_method": "createOrder",
  "files": ["src/OrderController.java", "src/OrderService.java"]
}
```

文件内容：
- `OrderController.java` → `public Order createOrder(OrderDTO dto) {...}`
- `OrderService.java` → `public Order createOrder(OrderDTO dto) { orderMapper.insert(o); ...}`

组装后（节选）：
```
分析以下 API 端点：

**端点**: POST /api/orders
**入口方法**: OrderController.createOrder

**代码**:
```java
// OrderController.java
public Order createOrder(OrderDTO dto) {
    return orderService.createOrder(dto);
}
// OrderService.java
public Order createOrder(OrderDTO dto) {
    Order order = new Order();
    orderMapper.insert(order);
    return order;
}
```

请输出 6 个部分...
```

### 示例：期望的 LLM 输出

```
=== 调用时序 ===
客户端 POST /api/orders {item_id, quantity}
  → OrderController.createOrder(OrderDTO)
    → OrderService.createOrder(OrderDTO)
      → OrderMapper.insert(Order) — 持久化到 DB
    → 返回 Order(id=12345, status="CREATED")
  → 客户端收到 201 Created + Order详情
```

常见失败模式：
- 缺少箭头（无 `→`）— 软警告，不阻塞
- 方法名错误 — 对照 `{CLASS}.{METHOD}` 元数据核实
- 部分为空 — 写入 `=== 状态: 失败 ===` 标记

## Step 3 — 解析并构建 JSONL

```bash
python scripts/parse_analysis.py --dir output/analyses --groups output/file_groups.json --output output/analysis_results.jsonl [--strict]
```

读取所有 `.md` 分析文件，解析 6 部分格式，提取结构化数据，构建 aggregator 所需的 JSONL。

**失败处理：**
- 标记了 `=== 状态: 失败 ===` 的文件，写为 `success: false` 条目 — aggregator 自动跳过
- 若解析因缺少部分而失败，脚本警告具体簇和部分 — 重新运行该簇的分析（Step 2）
- 加 `--strict` flag 使空部分警告导致非零退出码（适用于 CI）

## Step 4 — 聚合 + HTML

```bash
python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

Aggregator 静默跳过 `success: false` 的条目。最终 HTML 仅包含成功分析的簇。

## Step 5 — 验证（必须）

```bash
python scripts/verifier.py --input output/final_model.json
```

**此步必须执行。**跳过则可能交付包含臆造规则、缺失步骤或错误调用链的文档。verifier 通过对照原始代码交叉检查来发现这些问题。

## Step 5b — 用户确认（必须）

verifier 完成后，向用户展示结果并等待确认：

```
验证完成：成功 M 个，纠正 K 个
纠正详情：
- cluster_id: 字段「规则」描述与代码不符 → 已修正为「xxx」
- cluster_id: 调用链缺少「库存扣减」步骤 → 已补充

请确认处理方式：
[A] 接受纠正，继续生成HTML
[B] 重新分析失败簇（需提供cluster_id列表）
[C] 放弃本次分析
```

**未经用户确认不得进入 Step 6。** 若用户选择 [B]，继续重新分析；若选 [C]，停止并报告部分结果。

## Step 6 — 组装 HTML

```bash
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

## Step 7 — 大型项目（>50 簇）

- 考虑先用 `--mode overview` 获取高层地图，再深入特定模块
- 在最终报告中注明失败数量
- 若失败率 > 10%，调查是否存在系统性 LLM 问题（如不常见代码模式）

## Step 8 — 向用户报告

完成后告知用户：
- 分析了 N 个功能簇（成功 M 个，失败 K 个）
- 发现了哪些业务模块
- HTML 文件位置：`output/business_doc.html`
- 浏览器打开即可查看

若有失败，另报告：
- 失败的簇列表（cluster_id）
- 建议用户检查是否接受部分结果，或修复后重跑

## 重要规则

1. **分析结果保存为 `.md` 文件，不是 `.json`。** `parse_analysis.py` 脚本处理 JSON 转换。Markdown 对 LLM 输出更可靠。
2. **call_chain 格式** — 使用 `→` 箭头和缩进：
   ```
   客户端 → Controller.method(param)
     → Service.method(param) — 说明
       → Mapper.method(param) — 说明
     → 返回 Result<Type>
   ```
3. **不跳过任何簇。** `file_groups.json` 中的每个簇都必须有分析文件。
4. **簇失败时**，在分析文件中用 `=== 状态: 失败 ===` 标记及错误原因。aggregator 会标记但继续。不要静默跳过。
5. **始终执行 Step 5（verifier）和 Step 5b（用户确认）。** verifier 后，向用户展示结果并等待确认，方可进入 HTML 组装。