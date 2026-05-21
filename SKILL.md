---
name: code-to-business
description: 电商业务分析 Skill。从代码生成完整业务流图和文档。支持模块扫描、LLM 自动分析、Mermaid 图表生成及 HTML 报告组装。
version: "4.1"
---

# 电商业务分析 Skill

扫描代码仓库，提取业务逻辑，生成带 Mermaid 时序图/泳道图、异常分支表、数据表映射的业务文档。

## 触发词
- "分析电商业务"、"梳理业务流程"、"生成业务文档"

## 核心工作流 (8 阶段)

### Step 0: 初始设置
```bash
mkdir -p output/analyses
```

### Step 1: 模块扫描与文件收集
识别微服务边界，将 Controller/Service 按功能簇分组。
```bash
python scripts/collector.py --target <PROJECT_PATH> --mode deep --output output/file_groups.json
```

### Step 2: LLM 业务分析 (核心)
对每个簇进行分析。**开始前必须阅读 `references/formatting_guidelines.md`。**
1. 准备 Prompt (见 `references/prompt_template.md`)。
2. 调用 LLM 生成 API 入口、时序图、泳道图、异常表、数据表映射。
3. 将输出保存为 `output/analyses/<cluster_id>.md`。

### Step 3: 解析并构建 JSONL
```bash
python scripts/parse_analysis.py --dir output/analyses --groups output/file_groups.json --output output/analysis_results.jsonl
```

### Step 4: 聚合数据模型
```bash
python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json
```

### Step 5: 源码交叉验证 (必做)
```bash
python scripts/verifier.py --results output/analysis_results.jsonl --groups output/file_groups.json --config config.yaml --output output/verified_results.jsonl
```

### Step 6: 用户确认
展示验证结果（修正项、失败项），征得用户同意后进入下一步。

### Step 7: 组装 HTML 报告
```bash
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

## 资源导航

- **输出格式规范**：详见 `references/formatting_guidelines.md`。
- **Mermaid 写法参考**：详见 `references/mermaid_recipes.md`。
- **Prompt 模板**：详见 `references/prompt_template.md`。
- **执行约束与排错**：详见 `references/troubleshooting.md`。

## 脚本清单 (CLI 签名)

| 脚本 | 用途 |
|--------|---------|
| `collector.py` | 收集 Java 文件，按功能簇分组 |
| `parse_analysis.py` | 解析 Markdown 分析结果 → JSONL |
| `aggregator.py` | 合并条目生成最终数据模型 |
| `verifier.py` | 对照源代码二次校验分析结果 |
| `html_assembler.py` | 组装生成 HTML 业务文档 |

---
**注意**：始终遵循 `references/troubleshooting.md` 中的执行约束，确保报告的真实性与准确性。
