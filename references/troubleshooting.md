# code-to-business 执行约束与错误排查

本文件提供了在执行业务分析过程中的约束条件、常见失败场景的应对方案以及边界情况处理。

## 1. 执行约束 (Execution Constraints)

1. **源码驱动**：必须实际读取代码文件进行分析，严禁基于类名或方法名进行盲猜或假设。
2. **图表必选**：每个核心业务流程（如登录、下单、支付）必须生成对应的 Mermaid 时序图和泳道图。
3. **真实映射**：报告中必须标注代码中实际存在的数据表名和 API 路径。
4. **验证流程**：始终执行 Step 5 (verifier) 和 Step 5b (用户确认)，未经确认不得生成最终 HTML。

## 2. 常见失败场景及应对

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| `file_groups.json` 为空 | 源码路径错误或项目结构不标准 | 检查 `python scripts/collector.py` 的 `--target` 参数 |
| LLM 返回不完整 | 模型输出被截断或网络波动 | 标记该簇为失败，并在 Step 2c 中针对该簇重分析 |
| Mermaid 语法错误 | 模型输出格式瑕疵 | 记录警告但继续；重试时在提示词中强调 `sequenceDiagram` 语法 |
| 验证结果不匹配 | LLM 幻觉或逻辑理解偏差 | 参考 verifier 建议，手动修正或重新发起该簇的深度分析 |
| HTML 生成失败 | `final_model.json` 损坏 | 检查 aggregator 运行日志，确保 JSONL 解析无误 |

## 3. 边界条件速查

- **0 个分析簇**：提前终止并向用户报告，检查 collector 扫描范围。
- **超大规模项目 (>100 簇)**：启用分批处理模式，每批 20-30 个，建立检查点。
- **文件路径含空格**：确保在 CLI 调用中使用双引号包裹路径。
- **LLM 超时**：脚本应具备自动保存已获取部分的能力，标记失败簇以便续传。

## 4. 调试模式 (Debug Mode)

如需排查具体脚本逻辑，可尝试以下命令：

```bash
# 验证 collector 收集结果
python scripts/collector.py --target <PATH> --mode deep --output /dev/stdout

# 详细模式运行解析器
python scripts/parse_analysis.py --dir output/analyses --groups file_groups.json --output test.jsonl --verbose

# 检查聚合器跳过的条目
python scripts/aggregator.py --results analysis_results.jsonl --output /dev/stdout 2>&1 | grep -i skip
```
