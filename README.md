# code-to-business — OpenCode Skill

**Java 代码 → 业务文档翻译器**

OpenCode 原生 skill。把你公司的 Java 代码变成非技术人员也能看的 HTML 业务文档，带 Mermaid 时序图和流程图。**LLM 分析用你 OpenCode 已配好的公司模型，无需额外对接。**

---

## 安装

```bash
# 方式一：clone 到 OpenCode skills 目录
git clone https://github.com/kodak9527/code-to-business.git ~/.config/opencode/skills/code-to-business

# 方式二：放在项目里（OpenCode 自动发现）
git clone https://github.com/kodak9527/code-to-business.git
```

## 使用

对 OpenCode 说：

```
用 code-to-business 分析 /path/to/java-project，生成业务文档
```

OpenCode 自动加载 SKILL.md，按四步执行：

```
collector.py → OpenCode LLM 分析 → parse_analysis.py → HTML 文档
```

## 管线详解

| 步骤 | 谁做 | 命令/动作 |
|------|------|-----------|
| 1 收集 | 脚本 | `python scripts/collector.py --target <path> --mode deep` |
| 2 分析 | **OpenCode LLM** | 用自己的模型 + prompt 模板，产出 markdown |
| 3 解析 | 脚本 | `python scripts/parse_analysis.py` 转 JSONL |
| 4 组装 | 脚本 | `aggregator.py` + `html_assembler.py` 生成 HTML |
| 5 验证 | 脚本 | `python scripts/verifier.py` 完整性检查 |

## 目录结构

```
code-to-business/
├── SKILL.md                  ← OpenCode 自动加载（执行指令）
├── AGENTS.md                 ← 项目上下文（快速参考）
├── README.md
├── scripts/
│   ├── collector.py          # 收集 Java 文件，按功能簇分组
│   ├── parse_analysis.py     # 解析 LLM 产出的 markdown → JSONL
│   ├── build_jsonl.py        # 合并单文件 JSON（备用）
│   ├── aggregator.py         # 聚合 + Mermaid 图表生成
│   ├── html_assembler.py     # 生成自包含 HTML
│   └── verifier.py           # 完整性验证
└── references/
    ├── prompt_template.md    # LLM Prompt 模板（6部分格式）
    └── mermaid_recipes.md    # Mermaid 写法参考
```

## 输出

`output/` 目录：
- `business_doc.html` — 浏览器直接打开
- `file_groups.json` — 收集阶段产物
- `analyses/` — LLM 分析 markdown 文件
- `analysis_results.jsonl` — 合并结果
- `final_model.json` — 最终数据模型

## License

MIT
