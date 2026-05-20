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
collector.py → OpenCode LLM 分析 → parse_analysis.py → aggregator.py → verifier.py → [用户确认] → html_assembler.py / markdown_assembler.py
```

## 管线详解

| 步骤 | 谁做 | 命令/动作 |
|------|------|-----------|
| 1 收集 | 脚本 | `python scripts/collector.py --target <path> --mode deep` |
| 2 分析 | **OpenCode LLM** | 用自己的模型 + prompt 模板，产出 markdown |
| 3 解析 | 脚本 | `python scripts/parse_analysis.py` 转 JSONL |
| 4 聚合 | 脚本 | `python scripts/aggregator.py` 生成 final_model.json |
| 5 验证 | 脚本 | `python scripts/verifier.py` 对照源码二次校验 |
| 5b 用户确认 | 你 | 查看验证结果，选择接受纠正或重新分析 |
| 6 组装 | 脚本 | `html_assembler.py` / `markdown_assembler.py` 生成文档 |

可选参数 `--audience newcomer` 生成面向产品经理/运维的新人引导版。

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

## 输出格式

支持**多受众**输出（`--audience technical` 或 `--audience newcomer`）：

| 格式 | 受众 | 说明 |
|------|------|------|
| `business_doc.html` | 技术人员 | 带 Mermaid 时序图、侧边栏导航、暗色模式 |
| `business_doc_newcomer.html` | 产品经理/运维 | 术语提示、面包屑导航、运维关注点、数据表格化 |
| `business_doc_newcomer.md` | 产品经理/运维 | Markdown 格式，含术语表和表格化数据模型 |

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
│   ├── html_assembler.py     # 生成自包含 HTML（支持多受众）
│   ├── markdown_assembler.py # 生成 Markdown（支持多受众）
│   └── verifier.py           # 完整性验证
└── references/
    ├── prompt_template.md    # LLM Prompt 模板（6部分格式）
    └── mermaid_recipes.md    # Mermaid 写法参考
```

## License

MIT
