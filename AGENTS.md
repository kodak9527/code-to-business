# AGENTS.md — OpenCode Instructions

## What This Repo Does

`code-to-business` transforms a Java codebase into business documentation that non-engineers can read. HTML output with Mermaid sequence diagrams and flowcharts.

## Pipeline (4 steps — OpenCode handles the LLM)

```
Java Source ──▶ collector.py ──▶ 💬 OpenCode LLM ──▶ aggregator.py ──▶ html_assembler.py ──▶ business_doc.html
```

**Your LLM is the engine.** You read the code, analyze it with the prompt template, save results, then the scripts assemble the HTML.

## Quick Start (for you, the OpenCode agent)

When the user says "分析这个 Java 项目" or "用 code-to-business 生成业务文档":

### Step 1 — Collect

```bash
python scripts/collector.py --target <用户指定的路径> --mode deep --output output/file_groups.json
```

This scans all Java files, groups them by feature cluster (Controller + its call chain).

### Step 2 — You Do the LLM Analysis

This is the core step. For EACH cluster in `output/file_groups.json`:

1. Read the cluster metadata (http_method, http_path, entry_class, entry_method, endpoints)
2. Read the Java source files listed in `files[]` 
3. Use the prompt template from `references/prompt_template.md` — the system prompt and user prompt template are both there
4. Ask your LLM to produce the 6-part analysis:
   - === 业务概述 ===  (100-200字大白话)
   - === 业务流程 ===  (分步骤)
   - === 关键业务规则 ===  (列表)
   - === 调用时序 ===  (缩进箭头格式)
   - === 数据模型 ===  (列表)
   - === 异常/边界情况 ===
5. Save as JSON file: `output/analyses/<cluster_id>.json`

Analysis JSON format (参考模板):
```json
{
  "cluster_id": "order_001",
  "mode": "deep",
  "http_method": "POST",
  "http_path": "/api/orders",
  "entry_class": "OrderController",
  "entry_method": "createOrder",
  "endpoints": ["POST /api/orders"],
  "success": true,
  "parsed": {
    "summary": "创建订单接口，用户提交商品信息后...",
    "flow": [
      "步骤1: 用户提交订单请求 → 系统接收订单数据",
      "步骤2: 校验商品库存 → 库存充足则继续",
      "步骤3: 锁定库存并生成订单 → 订单写入数据库",
      "步骤4: 返回订单号和状态 → 用户看到下单成功"
    ],
    "rules": [
      "规则1: 库存不足时拒绝下单，返回错误提示",
      "规则2: 同一用户重复提交检测"
    ],
    "exceptions": "库存不足、商品已下架、重复提交会被拦截",
    "data_models": [
      "OrderDTO: 订单请求体，包含商品ID、数量、收货地址",
      "Order: 订单实体，包含订单号、状态、金额"
    ],
    "call_chain": "客户端 → OrderController.createOrder(OrderDTO)\n  → OrderServiceImpl.createOrder(dto) — 创建订单\n    → InventoryService.deductStock(skuId, qty) — 扣减库存\n    → OrderMapper.insert(order) — 写入数据库\n  → 返回 Result<Long>(orderId)"
  }
}
```

> ⚠️ call_chain 格式很重要：用 `→` 箭头和缩进表示调用层级，aggregator 会从中生成 Mermaid 时序图。

### Step 3 — Build JSONL

```bash
python scripts/build_jsonl.py --dir output/analyses --output output/analysis_results.jsonl
```

This combines all individual analysis JSON files into the JSONL format aggregator expects.

### Step 4 — Aggregate + HTML

```bash
python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

### Step 5 — Verify (optional)

```bash
python scripts/verifier.py --input output/final_model.json
```

## Report

After running, tell the user:
- How many feature clusters were analyzed
- What business modules were found
- Where the HTML file is: `output/business_doc.html`
- Open it in a browser

## Tips

- For large projects (>50 clusters), batch the analysis — do ~10 clusters per turn
- If an analysis JSON is malformed, aggregator.py will report which cluster_id failed
- The `call_chain` field drives the Mermaid sequence diagram — make sure the arrow format is clean
- All paths are relative to the repo root
- Create `output/analyses/` directory before saving analysis files
