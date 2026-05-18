# code-to-business

**Java 代码 → 业务文档翻译器**

把公司内部 Java 代码仓库翻译成非技术人员也能看懂的业务文档，全程代码不出内网。

---

## 核心能力

- **注释收集** — 提取 Java 源码中的 Class/Method 注释
- **业务语义分析** — 通过 LLM（大模型）理解代码的业务意图
- **聚合输出** — 合并为结构化 JSON，便于后续处理
- **HTML 文档生成** — 输出带样式、流程图、时序图的业务文档
- **自我验证** — 自动检查文档完整性，漏掉的接口/实体会有警告

---

## 目录结构

```
code-to-business/
├── SKILL.md                    # Skill 元信息与使用说明
├── config.example.yaml         # 配置文件示例
├── scripts/
│   ├── collector.py            # 步骤1：收集 Java 源文件 & 注释
│   ├── llm_analyzer.py          # 步骤2：LLM 业务语义分析
│   ├── aggregator.py            # 步骤3：聚合为中间 JSON
│   ├── html_assembler.py        # 步骤4：生成 HTML 业务文档
│   └── verifier.py              # 步骤5（可选）：自我验证
├── references/
│   ├── prompt_template.md       # LLM prompt 模板
│   └── mermaid_recipes.md       # Mermaid 流程图/时序图写法参考
└── README.md
```

---

## 快速开始

### 1. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入 LLM API 地址/密钥、代码仓库路径
```

### 2. 运行

```bash
python scripts/collector.py --config config.yaml
python scripts/llm_analyzer.py --config config.yaml [--verify]
python scripts/aggregator.py --config config.yaml
python scripts/html_assembler.py --config config.yaml
python scripts/verifier.py --config config.yaml --input output/
```

### 3. 输出

`output/` 目录下生成：
- `business_doc.html` — 可直接在浏览器打开的业务文档
- `aggregated.json` — 中间聚合数据（可供其他工具二次处理）

---

## 工作流示意

```
Java 源码  ──▶  collector.py  ──▶  llm_analyzer.py  ──▶  aggregator.py
              (收集注释)       (LLM业务分析)         (聚合JSON)
                                                              │
                                                              ▼
                                          verifier.py ◀── html_assembler.py
                                          (自我验证)         (生成HTML)
```

---

## 关于 Mermaid 图表

`references/mermaid_recipes.md` 提供了常用图表的写法参考：

- **流程图** — 业务判断逻辑
- **时序图** — 接口调用顺序
- **类图** — 实体关系
- **状态图** — 状态机流转

生成后的 HTML 里的 Mermaid 块会自动渲染。

---

## License

MIT
