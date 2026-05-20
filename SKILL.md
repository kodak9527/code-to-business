---
name: code-to-business
description: 电商业务分析 Skill。将 Java 代码转换为业务文档。当被要求"分析电商业务"、"梳理业务流程"、"生成本业务文档"时使用。直接在 OpenCode 中工作 — 扫描 Service/Controller/DAO 层，追踪核心调用链，生成带 Mermaid 图的业务文档。
version: "3.0"
tags:
  - java
  - documentation
  - business-analysis
  - e-commerce
  - opencode
examples:
  - "分析电商业务"
  - "梳理业务流程"
  - "生成本业务文档"
---

# code-to-business — 电商业务分析 Skill

## 触发词

当用户说以下内容时，激活本 Skill：
- "分析电商业务"
- "梳理业务流程"
- "生成本业务文档"

## 分析维度（必做）

### 1. 模块扫描
定位项目中所有：
- **Service 层**：业务逻辑核心
- **Controller 层**：对外 API 入口
- **DAO/Mapper 层**：数据访问层

### 2. 入口识别
找到所有对外 API 入口，记录：
- HTTP 方法 + 路径
- 入口类和方法
- 请求参数概要

### 3. 流程追踪
追踪**至少 5 个核心用户操作**的完整调用链，包括：
- 车辆销售相关流程
- 企业客户相关流程
- 支付/订单流程
- 用户操作流程

### 4. 数据流标注
记录每个操作涉及：
- 数据表（MySQL/Oracle）
- 缓存（DCS/Redis）
- 外部服务调用

## 重点关注模块

以下模块需要重点分析：

| 模块类型 | 说明 |
|---------|------|
| 车辆销售模块 | 整车销售、库存管理、价格计算 |
| 企业客户模块 | 企业客户管理、授信、结算 |
| 支付/订单模块 | 支付通道、订单状态、优惠券 |
| 缓存使用场景 | DCS/Redis 缓存策略、缓存键设计 |

## 脚本清单

| 脚本 | 用途 | 关键 CLI 签名 |
|--------|---------|-------------------|
| `scripts/collector.py` | 收集 Java 文件，按功能簇分组 | `--target <PATH> --mode [deep\|overview] --output <FILE>` |
| `scripts/parse_analysis.py` | 解析 LLM markdown 输出 → JSONL | `--dir <ANALYSES_DIR> --groups <FILE_GROUPS> --output <JSONL>` |
| `scripts/aggregator.py` | 合并 JSONL 条目 → final_model.json | `--results <JSONL> --output <MODEL_JSON>` |
| `scripts/verifier.py` | 对照源代码交叉检查分析结果 | `--results <JSONL> --groups <FILE_GROUPS> --config <CONFIG> --output <VERIFIED_JSONL>` |
| `scripts/html_assembler.py` | 生成 HTML 业务文档 | `--model <MODEL_JSON> --output <HTML>` |

**参考文件**: `references/prompt_template.md` — 用于 LLM 分析的系统提示和用户提示模板。

## 开始前必做

执行任何步骤前，验证所有资源和脚本可用：

```bash
# 验证脚本存在且可执行
for script in scripts/collector.py scripts/parse_analysis.py scripts/aggregator.py scripts/verifier.py scripts/html_assembler.py; do
  if [ ! -f "$script" ]; then echo "MISSING: $script"; exit 1; fi
  if [ ! -r "$script" ]; then echo "UNREADABLE: $script"; exit 1; fi
done

# 验证 references 存在
if [ ! -f "references/prompt_template.md" ]; then echo "MISSING: references/prompt_template.md"; exit 1; fi

# 验证 Python 依赖（collector.py 需要 pyyaml）
python -c "import yaml" 2>/dev/null || echo "WARNING: pyyaml not available"
```

若任何检查失败，停止并报告缺失资源。

## 流程概览

```
collector.py → [LLM 分析] → parse_analysis.py → aggregator.py → verifier.py → [用户确认] → html_assembler.py
```

你的任务：扫描模块、追踪调用链、生成带 Mermaid 图的业务文档。

## Step 0 — 初始设置（仅首次）

```bash
mkdir -p output/analyses
```

## Step 1 — 模块扫描 + 收集 Java 文件

### 1a. 扫描项目结构

分析项目时，首先识别：

**Service 层**：查找 `*Service.java`、`*ServiceImpl.java`
**Controller 层**：查找 `*Controller.java`
**DAO 层**：查找 `*DAO.java`、`*Mapper.java`

### 1b. 收集 Java 文件

```bash
python scripts/collector.py --target <PROJECT_PATH> --mode deep --output output/file_groups.json
```

- `--mode deep`：每个 Controller 方法一个簇（推荐）
- `--mode overview`：每个 Controller 类一个簇

阅读输出，了解有多少个簇待分析。

### 1c. 标记重点模块

在收集结果中，标记以下模块为**重点分析对象**：
- 车辆销售相关（包含 `Vehicle`、`Car`、`Sales`、`Stock` 等关键词）
- 企业客户相关（包含 `Enterprise`、`Customer`、`Credit` 等关键词）
- 支付/订单相关（包含 `Pay`、`Order`、`Payment`、`Trade` 等关键词）
- 缓存相关（包含 `Cache`、`Redis`、`DCS` 等关键词）

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

发送系统提示 + 用户提示。期望返回 6 个部分，格式必须严格遵循：

**1. `=== 业务概述 ===`**
- 100-200 字，一段话，大白话
- 从用户视角：用户做了什么操作，系统返回了什么
- 禁止出现类名、方法名、代码术语
- 示例：`客户提交订单后，系统创建订单记录，返回订单号和预计发货时间`

**2. `=== 业务流程 ===`**
- 编号列表，每步格式：`步骤N: 做什么 → 得到什么结果`
- 步骤顺序必须与调用时序一致
- 每个步骤都要有用户可见的动作和系统响应
- 示例：`步骤1: 客户填写订单信息并提交 → 系统验证库存`

**3. `=== 关键业务规则 ===`**
- 无序列表（`-`），每条规则格式：`规则描述: 具体条件或逻辑`
- 只写代码中明确实现的 if/else/validate 逻辑
- 禁止编造规则；没有则写 `无明显业务规则`
- 示例：`- 库存扣减: 下单时立即扣减库存，不预留`

**4. `=== 调用时序 ===`**
- 缩进箭头链，必须包含 `→` 箭头
- 格式严格遵循：
  ```
  客户端 → Controller.method(参数含义)
    → Service.method(参数含义) — 这一步做了什么
      → Mapper.method(参数含义) — 操作了什么数据
    → 返回 Result<类型> 给客户端
  ```
- 每层缩进 2 空格；参数要写明含义，不能只是变量名

**5. `=== 数据模型 ===`**
- 列出涉及的主要 Java 类及其字段
- 格式：
  ```
  - ClassName: 用途简述
    - fieldName (Type): 字段含义
  ```
- 示例：
  ```
  - OrderDTO: 客户提交的订单数据
    - itemId (Long): 商品ID
    - quantity (Integer): 购买数量
  ```

**6. `=== 异常/边界情况 ===`**
- 无序列表，每条说明一种异常及处理方式
- 格式：`情况描述 → 处理逻辑`
- 没有异常处理则写 `无特殊异常处理`
- 示例：`库存不足 → 返回错误码 E100，提示客户库存不够`

### Step 2d — 分析后检查（检查点 2）

LLM 返回后，验证输出结构：

**6 部分检查** — 确认每个部分都存在：
- 必须包含全部 6 个 section header
- 缺失任意部分 → 记为部分失败，文件中包含标记并注明缺失的部分

**调用链格式检查** — 若 `=== 调用时序 ===` 非空，确认包含 `→` 箭头：
- 未找到 `→` → 文件中警告 call_chain 可能格式错误
- 这是软检查（非阻塞），我们对 LLM 有一定信任

**文件名检查** — 确认 `cluster_id` 与 `file_groups.json` 一致。

**失败决策树**：

```
验证结果
├── 通过 → 进入 Step 2e
└── 失败（任一硬检查）
    ├── 写入 output/analyses/<cluster_id>.md，内容包含：
    │   "=== 状态: 失败 ===" + 失败原因 + 缺失部分列表
    └── 继续处理下一簇（不断开流程）
```

**不因单簇失败而停止整批。** 所有簇处理完毕后，在 Step 3 之前统计失败数。

### Step 2e — 保存为 Markdown

将 LLM 原始输出保存到 `output/analyses/<cluster_id>.md`（不是 JSON）。

文件名必须与 `file_groups.json` 中的 `cluster_id` 匹配。

### Step 2f — 输出质量检查清单（自检）

分析完成后、进入 Step 3 之前，对照以下清单逐项核对：

- [ ] **业务概述** — 是大白话吗？非技术人员能看懂吗？
- [ ] **业务流程** — 步骤顺序与调用时序一致吗？每步都有用户动作和系统响应吗？
- [ ] **关键业务规则** — 规则在代码里有对应逻辑吗？有没有编造？
- [ ] **调用时序** — 包含 `→` 箭头吗？每步都写明了参数含义吗？
- [ ] **数据模型** — 字段名和类型与代码一致吗？字段含义准确吗？
- [ ] **异常/边界情况** — 列出的异常在代码中有对应处理吗？
- [ ] **幻觉检查** — 整个输出中有没有出现代码里不存在的类名、方法名、字段、规则？
- [ ] **敏感信息检查** — 是否包含密码、密钥、手机号等敏感信息？如有需脱敏

任一硬性问题（如幻觉内容、调用链缺箭头）→ 标记失败并重分析。
软性问题（如表述不够大白话）→ 记录但不阻塞，可接受但需改进。

### 批量处理 + 断点续传策略

**何时分批**：簇数量 > 20 的项目需要分批处理；≤20 可一轮完成。

**分批操作**：
```
第1轮：处理簇 1-10，写入 output/analyses/
第2轮：处理簇 11-20，写入 output/analyses/
...持续直到全部完成
```

**续传逻辑**（最关键的保障）：
```
重新运行 Step 2 时，脚本检查 output/analyses/
  → 已有对应 .md 文件的簇 → 跳过（读取而非重写）
  → 没有 .md 文件的簇 → 正常分析
因此：任意时刻中断 → 重新运行 Step 2 → 自动从断点继续，不会重复已成功的簇
```

**失败簇的续传特殊处理**：
- 失败簇的 .md 文件也存在于 `output/analyses/`（内容含 `=== 状态: 失败 ===`）
- 若想重试失败簇 → 必须先手动删除其 .md 文件 → 重新运行 Step 2
- 不删除直接重跑会被跳过

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

## Step 4 — 聚合（生成 final_model.json）

```bash
python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json
```

Aggregator 静默跳过 `success: false` 的条目。最终数据模型仅包含成功分析的簇。

**注意**：此步只生成 `final_model.json`，不生成 HTML。HTML 生成在 Step 6（用户确认之后）。

## Step 5 — 验证（必须）

```bash
python scripts/verifier.py \
  --results output/analysis_results.jsonl \
  --groups output/file_groups.json \
  --config config.yaml \
  --output output/verified_results.jsonl
```

**此步必须执行。** 跳过则可能交付包含臆造规则、缺失步骤或错误调用链的文档。verifier 对每条成功分析进行二次校验，对照原始代码挑错。

**verifier 输出的统计指标**：
- `total`：需要校验的条目数
- `verified`：校验通过（无修正）
- `corrected`：发现并接受了修正
- `failed`：校验调用失败（网络错误等）
- `skipped`：已跳过（失败条目或 dry-run）

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

**未经用户确认不得进入 Step 6。** 分支处理：

| 用户选择 | 你应该做什么 |
|---------|-------------|
| [A] | 进入 Step 6，执行 `html_assembler.py` |
| [B] | 收集用户提供的 cluster_id 列表，从对应 `.md` 文件删除后重新运行 Step 2c |
| [C] | 停止，输出 `output/analyses/` 中已有的分析文件位置，告知用户可后续合并 |

**若用户超时无响应，不自动继续。** 等待明确指令。

## Step 6 — 组装 HTML

```bash
python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html
```

### 输出规范（重要）

生成的 HTML 文档必须满足：

| 规范 | 说明 |
|------|------|
| **独立章节** | 每个核心流程独立章节，有清晰的标题和序号 |
| **Mermaid 图** | 时序图和流程图放在对应章节内，不要放附录 |
| **敏感信息脱敏** | 手机号、身份证、密码、密钥等必须用 `***` 替代 |
| **数据表标注** | 每个流程涉及的数据表需要标注（如 `orders`、`inventory`） |
| **缓存标注** | 需要标注 DCS/Redis 缓存的读写操作 |

## Step 7 — 大型项目（>50 簇）

**推荐的两阶段策略**：

1. **第一阶段 — 全局地图**（用 `--mode overview`）
   - 快速生成所有簇的高层概览（每个 Controller 一个簇而非每个方法一个簇）
   - 目的：了解业务模块划分，识别值得深入的区域

2. **第二阶段 — 深度分析**（用 `--mode deep`）
   - 仅对高价值模块的 Controller 使用 deep 模式
   - 其他模块用 overview 结果即可，无需全部 deep

**失败率监控**：
- 失败率 > 10% → 调查系统性原因（不常见代码模式 / LLM 幻觉模式）
- 在最终报告中注明：分析了 N 个簇，成功 M 个，失败 K 个

## Step 8 — 向用户报告

完成后告知用户：
- 分析了 N 个功能簇（成功 M 个，失败 K 个）
- 发现了哪些业务模块
- 重点分析了哪些模块（车辆销售/企业客户/支付订单/缓存）
- HTML 文件位置：`output/business_doc.html`
- 浏览器打开即可查看

若有失败，另报告：
- 失败的簇列表（cluster_id）
- 建议用户检查是否接受部分结果，或修复后重跑

## 错误排查与边界情况

### 常见失败场景及应对

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| `file_groups.json` 为空或格式错误 | collector.py 运行失败 | 检查 Java 源码路径是否正确；确认 `--mode` 参数有效 |
| LLM 返回不完整（缺 section） | 模型输出被截断或网络中断 | 该簇标记为失败，重新运行 Step 2c |
| `=== 调用时序 ===` 无 `→` 箭头 | LLM 格式遵循问题 | 软警告，记录但继续；重分析时可强调格式要求 |
| 分析文件数量 < 簇数量 | 某些簇元数据校验失败 | 检查 `output/analyses/` 中标记为失败的文件 |
| verifier 报告规则不匹配 | LLM 幻觉或代码理解错误 | 重新分析对应簇；如持续失败，记录为已知限制 |
| HTML 生成失败 | `final_model.json` 结构异常 | 检查 aggregator 是否成功运行；查看脚本错误输出 |

### 边界条件速查

- **0 个簇**：collector 未找到任何 Controller/Service，提前终止并报告
- **1 个簇**：正常运行，不影响流程
- **大量簇（>100）**：分批处理，每批 20-30 个，设置检查点
- **Java 文件路径含空格**：脚本需用引号包裹路径（已由 collector.py 处理）
- **LLM 超时**：保存已获取的部分，标记为部分失败

### 调试模式

若问题难定位，使用以下命令获取详细输出：

```bash
# 单独运行 collector 并查看原始 JSON
python scripts/collector.py --target <PROJECT_PATH> --mode deep --output /dev/stdout

# 单独测试 parse_analysis
python scripts/parse_analysis.py --dir output/analyses --groups output/file_groups.json --output /tmp/test.jsonl --verbose

# 检查 aggregator 跳过哪些条目
python scripts/aggregator.py --results output/analysis_results.jsonl --output /dev/stdout 2>&1 | grep -i skip
```

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
6. **敏感信息脱敏。** 输出的文档中不得包含真实的手机号、身份证、密码、密钥等信息。
7. **每个流程独立章节。** Mermaid 图必须放在对应的流程章节内，不要放在附录。