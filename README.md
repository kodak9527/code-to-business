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

### 1. Clone & 配置

```bash
git clone https://github.com/kodak9527/code-to-business.git
cd code-to-business
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入 LLM API 地址/密钥
```

### 2. 一键运行

```bash
python cli.py run --target /path/to/your-java-project --config config.yaml
```

完毕。浏览器打开 `output/business_doc.html` 就是业务文档。

加 `--verify` 会在最后自动检查完整性：

```bash
python cli.py run --target /path/to/project --config config.yaml --verify
```

### 3. 分步运行（调试用）

```bash
python cli.py step 1 --target /path/to/project    # 只跑收集
python cli.py step 2 --config config.yaml          # 只跑LLM分析
python cli.py step 3                                # 只跑聚合
python cli.py step 4 --output 业务.html              # 只跑HTML
python cli.py step 5                                # 只跑验证
```

### 4. 输出

`output/` 目录：
- `business_doc.html` — 浏览器直接打开的业务文档
- `file_groups.json` — 收集阶段产物
- `analysis_output.json` — LLM分析产物
- `final_model.json` — 聚合后的最终数据模型

---

## 给 OpenCode 用

这个仓库自带 `AGENTS.md`，OpenCode 进入目录后会自动读取。直接对 OpenCode 说：

```
用 code-to-business 分析 /path/to/java-project，生成业务文档
```

OpenCode 会自动完成配置检查 → 运行管线 → 输出报告。

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
