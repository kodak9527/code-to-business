---
name: code-to-business
description: Transform Java code into business documentation. Use when asked to analyze Java projects, generate business docs from code, or explain Java interfaces to non-engineers. Works directly in OpenCode — run collector, use your LLM for the 6-part analysis, then assemble HTML with Mermaid diagrams.
---

# code-to-business — OpenCode Agent Instructions

You are executing the code-to-business pipeline. Follow these steps in order.

## Pipeline Overview (updated)

```
collector.py → [YOU — LLM analysis] → parse_analysis.py → aggregator.py → verifier.py → [USER REVIEW] → html_assembler.py
```

Your job: run the collector, do the LLM analysis using the prompt template, then let the scripts assemble the HTML.

## Setup (first time only)

```bash
mkdir -p output/analyses
```

## Step 1 — Collect Java Files

```bash
python scripts/collector.py --target <PROJECT_PATH> --mode deep --output output/file_groups.json
```

`--mode deep`: one cluster per Controller method (recommended).
`--mode overview`: one cluster per Controller class.

Read the output to understand how many clusters you'll be analyzing.

## Step 2 — LLM Analysis (this is where you work)

Read `references/prompt_template.md` — it contains the system prompt and user prompt template.

For **each** cluster in `output/file_groups.json`:

### 2a. Prepare the prompt

Read the cluster's Java files (listed in `files[]`). Read the cluster metadata (`http_method`, `http_path`, `entry_class`, `entry_method`).

Assemble the user prompt by replacing placeholders in the template:
- `{HTTP_METHOD} {PATH}` — from cluster metadata
- `{CLASS}.{METHOD}` — from cluster metadata
- `{CODE_BLOCKS}` — the Java source files, concatenated

### 2b. Pre-analysis validation（检查点1）

Before calling LLM, verify the cluster is ready:

**Metadata check** — must have all required fields:
- `http_method`, `http_path`, `entry_class`, `entry_method` present and non-empty
- If any field is missing → skip this cluster, write `=== 状态: 失败 ===\n缺少必要元数据字段` to the `.md` file

**Code check** — verify Java files exist and are readable:
- For each path in `files[]`, confirm the file exists and has content (>10 bytes)
- If file missing → skip cluster, write failure marker with missing file name

Only proceed to 2c if validation passes.

### 2c. Call your LLM

Send system prompt + user prompt to your LLM. It will return 6 sections:
1. === 业务概述 === (100-200字大白话)
2. === 业务流程 === (numbered steps)
3. === 关键业务规则 === (bullet list)
4. === 调用时序 === (indented arrow chain)
5. === 数据模型 === (field descriptions)
6. === 异常/边界情况 ===

### 2d. Post-analysis quick check（检查点2）

After LLM returns, verify the output is structurally valid:

**6-section check** — confirm all sections are present:
- Must contain `=== 业务概述 ===`, `=== 业务流程 ===`, `=== 关键业务规则 ===`, `=== 调用时序 ===`, `=== 数据模型 ===`, `=== 异常/边界情况 ===`
- If any section header is missing → treat as partial failure, include the marker in the file but note which section is absent

**call_chain format check** — if `=== 调用时序 ===` section is non-empty, verify it contains `→` arrows:
- If no `→` found → warn in the file that call_chain may be malformed
- This is a soft check (non-blocking) since we trust LLM to some degree

**Filename check** — verify the cluster_id matches between `file_groups.json` and the output filename.

If checks pass, proceed to save. If failed, write failure marker with reason.

### 2e. Save as markdown

Save the raw LLM output to `output/analyses/<cluster_id>.md` (NOT JSON — we use a parser for reliability).

The filename must match `cluster_id` from `file_groups.json`.

### Batch processing strategy

For projects with many clusters (>20):
- Process ~10 clusters per turn
- Track which clusters are done by checking `output/analyses/` for `.md` files
- Continue until all clusters are done

**Resume tip:** If a turn ends mid-batch, simply re-run Step 2 — the script checks `output/analyses/` and skips clusters that already have `.md` files.

## Step 3 — Parse and Build JSONL

```bash
python scripts/parse_analysis.py --dir output/analyses --groups output/file_groups.json --output output/analysis_results.jsonl [--strict]
```

This reads all `.md` analysis files, parses the 6-section format, extracts structured data, and builds the JSONL that aggregator expects.

**Failure handling:**
- Files marked `=== 状态: 失败 ===` are written as `success: false` entries — aggregator skips them automatically.
- If parse fails due to missing sections, the script warns which cluster and which section is empty. Re-run that cluster's analysis (Step 2).
- Use `--strict` flag to make empty-section warnings cause non-zero exit code (useful for CI).

## Step 4 — Aggregate + HTML

```bash
python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

Aggregator silently skips entries with `success: false`. The final HTML will include only successfully analyzed clusters.

## Step 5 — Verify (required)

```bash
python scripts/verifier.py --input output/final_model.json
```

**This step is required.** Skipping it means you may deliver a document with hallucinated rules, missing steps, or incorrect call chains. The verifier catches these by cross-checking against the original code.

## Step 5b — User Review (REQUIRED)

After verifier completes, PRESENT results to the user and WAIT for confirmation:

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

**DO NOT proceed to Step 6 until user confirms.** If user chooses [B], proceed with re-analysis. If user chooses [C], stop and report partial results.

## Step 6 — Assemble HTML

```bash
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

## Step 7 — Large Projects (>50 clusters)

For very large projects, consider:
- Running with `--mode overview` first to get a high-level map, then deep-dive specific modules
- Noting the failure count in the final report to the user
- If failure rate > 10%, investigate whether a systematic LLM issue (e.g., unusual code patterns) is the cause

## Step 8 — Report to User

After completion, tell the user:
- 分析了 N 个功能簇（成功 M 个，失败 K 个）
- 发现了哪些业务模块
- HTML 文件位置: `output/business_doc.html`
- 浏览器打开即可查看

If there were failures, also report:
- 哪些簇失败了（cluster_id 列表）
- 建议用户检查是否接受部分结果，或修复后重跑

## Important Rules

1. **Save analysis as `.md` files, NOT `.json`.** The `parse_analysis.py` script handles JSON conversion. Markdown is more reliable for LLM output.
2. **call_chain format matters.** Use `→` arrows with indentation:
   ```
   客户端 → Controller.method(param)
     → Service.method(param) — 说明
       → Mapper.method(param) — 说明
     → 返回 Result<Type>
   ```
3. **Don't skip clusters.** Every cluster in `file_groups.json` must have an analysis file.
4. **If a cluster fails**, mark it in the analysis file with `=== 状态: 失败 ===` followed by the error reason. Example:
   ```
   === 状态: 失败 ===
   LLM returned empty response for call_chain section
   ```
   The aggregator will flag it but continue. Do not silently skip — always write the failure marker.
5. **Always run Step 5 (verifier) and Step 5b (user review).** After verifier, present results to user and wait for confirmation before proceeding to HTML assembly.
