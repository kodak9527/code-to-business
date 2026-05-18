# code-to-business — OpenCode 原生工具

**Java 代码 → 业务文档翻译器**

把公司内部 Java 代码仓库翻译成非技术人员也能看懂的业务文档，全程代码不出内网。**给 OpenCode 直接用的**——你的 OpenCode 已对接公司 LLM，无需额外配置。

---

## 管线

```
Java 源码 ──▶ collector.py ──▶ 💬 OpenCode LLM ──▶ aggregator.py ──▶ html_assembler.py ──▶ business_doc.html
```

**不需要 config.yaml。** LLM 分析这一步由 OpenCode 用自己已配置的公司模型完成。

---

## 在 OpenCode 中用

Clone 下来后对 OpenCode 说一句话：

```
用 code-to-business 分析 /path/to/our-java-project，生成业务文档
```

OpenCode 自动读 `AGENTS.md`，知道完整的四步管线。

---

## 手动命令行（调试用）

```bash
# 1. 收集
python scripts/collector.py --target /path/to/project --mode deep --output output/file_groups.json

# 2. LLM 分析 → 由 OpenCode 完成（参考 AGENTS.md 中的 JSON 格式）
#    每个功能簇保存为 output/analyses/<cluster_id>.json

# 3. 合并
python scripts/build_jsonl.py --dir output/analyses --output output/analysis_results.jsonl

# 4. 聚合 + HTML
python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html

# 5. 验证（可选）
python scripts/verifier.py --input output/final_model.json
```

---

## 目录结构

```
code-to-business/
├── AGENTS.md              ← OpenCode 自动加载，完整工作流说明
├── README.md
├── scripts/
│   ├── collector.py       # 收集 Java 文件，按功能簇分组
│   ├── build_jsonl.py     # 合并单文件分析结果为 JSONL
│   ├── aggregator.py      # 聚合 + Mermaid 图表生成
│   ├── html_assembler.py  # 生成自包含 HTML
│   └── verifier.py        # 完整性验证
├── references/
│   ├── prompt_template.md # LLM Prompt 模板
│   └── mermaid_recipes.md # Mermaid 图表写法参考
├── config.example.yaml    # 旧版 API 模式的配置（已废弃，保留供参考）
├── llm_analyzer.py        # 旧版 API 模式（已废弃，保留供参考）
└── cli.py                 # 旧版命令行入口（已废弃，保留供参考）
```

---

## 输出

`output/` 目录：
- `business_doc.html` — 浏览器直接打开的业务文档
- `file_groups.json` — 收集阶段产物
- `analyses/` — OpenCode 产出的单个分析 JSON
- `analysis_results.jsonl` — 合并后的分析结果
- `final_model.json` — 最终数据模型

---

## License

MIT
