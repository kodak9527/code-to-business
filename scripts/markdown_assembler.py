#!/usr/bin/env python3
"""
markdown_assembler.py — 将最终数据模型组装为 Markdown 文档

支持多受众：
  --audience technical (默认): 面向技术人员
  --audience newcomer: 面向产品经理和运维菜鸟（含术语表、表格化数据模型）

用法:
  python3 markdown_assembler.py --model final_model.json --output 业务文档.md
  python3 markdown_assembler.py --model final_model.json --output 业务文档.md --audience newcomer
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def build_markdown_technical(model: dict) -> str:
    """构建技术人员版 Markdown。"""
    lines = []
    lines.append(f"# {Path('output').stem} — 业务逻辑文档\n")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 共 {model['success_count']}/{model['total_apis']} 个接口\n")
    lines.append("")

    for api in model['apis']:
        if api.get('status') == 'failed':
            continue

        http_method = api.get('http_method', '')
        http_path = api.get('http_path', '')
        entry_class = api.get('entry_class', '')

        lines.append(f"## {http_method} {http_path}\n")
        lines.append(f"**入口类**: `{entry_class}`\n")

        if api.get('summary'):
            lines.append(f"\n### 业务概述\n{api['summary']}\n")

        if api.get('flow'):
            lines.append("\n### 业务流程\n")
            for i, step in enumerate(api['flow'], 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if api.get('rules'):
            lines.append("\n### 关键业务规则\n")
            for rule in api['rules']:
                lines.append(f"- {rule}")
            lines.append("")

        if api.get('data_models'):
            lines.append("\n### 数据模型\n")
            for model_item in api['data_models']:
                lines.append(f"- {model_item}")
            lines.append("")

        if api.get('call_chain'):
            lines.append("\n### 调用时序\n")
            lines.append("```\n")
            lines.append(api['call_chain'])
            lines.append("\n```\n")

        if api.get('exceptions'):
            lines.append(f"\n### 异常与边界情况\n{api['exceptions']}\n")

        lines.append("---\n")

    return '\n'.join(lines)


def build_markdown_newcomer(model: dict) -> str:
    """构建新人版 Markdown（含术语表、表格化数据模型、运维说明）。"""
    lines = []
    lines.append(f"# 业务文档 — 新人引导版\n")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 共 {model['success_count']}/{model['total_apis']} 个接口\n")
    lines.append("")

    # ========== 术语表 ==========
    lines.append("## 📖 术语表\n")
    lines.append("| 术语 | 解释 |")
    lines.append("|------|------|")
    terms = [
        ("API", "应用程序编程接口，系统与系统之间的对话窗口"),
        ("HTTP 方法", "GET=获取数据，POST=提交数据，PUT=更新数据，DELETE=删除数据"),
        ("接口", "API的另一个叫法，就像餐厅的菜单，告诉你能点什么菜"),
        ("调用链", "从发起请求到返回结果的完整路径，就像点外卖的整个流程"),
        ("参数", "调用接口时需要提供的信息，就像打电话需要拨打的号码"),
        ("返回码", "系统告诉你请求结果的方式。200=成功，400=请求错误，500=服务器错误"),
        ("幂等", "重复调用结果相同，不会产生副作用"),
    ]
    for term, definition in terms:
        lines.append(f"| **{term}** | {definition} |")
    lines.append("")

    # ========== 接口总览 ==========
    lines.append("## 📋 接口总览\n")
    lines.append("| 方法 | 路径 | 入口类 | 说明 |")
    lines.append("|------|------|--------|------|")
    for api in model['apis']:
        if api.get('status') == 'failed':
            continue
        http_method = api.get('http_method', '')
        http_path = api.get('http_path', '')
        entry_class = api.get('entry_class', '')
        summary = api.get('summary', '')[:50] + ('...' if len(api.get('summary', '')) > 50 else '')
        lines.append(f"| {http_method} | {http_path} | {entry_class} | {summary} |")
    lines.append("")

    # ========== 详细内容 ==========
    for api in model['apis']:
        if api.get('status') == 'failed':
            continue

        http_method = api.get('http_method', '')
        http_path = api.get('http_path', '')
        entry_class = api.get('entry_class', '')
        entry_method = api.get('entry_method', '')

        lines.append(f"## {http_method} {http_path}\n")
        lines.append(f"**入口**: `{entry_class}.{entry_method}()`\n")

        # 业务概述（新人版加解释）
        if api.get('summary'):
            lines.append(f"\n### 这段接口做什么\n")
            lines.append(f"> {api['summary']}\n")

        # 分步流程（带步骤编号）
        if api.get('flow'):
            lines.append("\n### 业务流程（共 {} 步）\n".format(len(api['flow'])))
            lines.append("跟着这个步骤走，就能完成整个操作：\n")
            for i, step in enumerate(api['flow'], 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        # 业务规则（加提示）
        if api.get('rules'):
            lines.append("\n### 关键业务规则\n")
            lines.append("> 💡 **记住**：这些规则决定了你能不能做某件事，以及做的时候要注意什么\n")
            for rule in api['rules']:
                lines.append(f"- {rule}")
            lines.append("")

        # 数据模型（表格形式）
        if api.get('data_models'):
            lines.append("\n### 数据模型\n")
            lines.append("| 字段 | 说明 |\n")
            lines.append("|------|------|\n")
            for model_item in api['data_models']:
                # 尝试解析 "ClassName: 用途" 格式
                if ':' in model_item:
                    parts = model_item.split(':', 1)
                    class_name = parts[0].strip()
                    desc = parts[1].strip()
                    lines.append(f"| **{class_name}** | {desc} |")
                else:
                    lines.append(f"| {model_item} | |")
            lines.append("")

        # 运维关注点
        ops_tips = build_ops_tips_md(api)
        if ops_tips:
            lines.append("\n### 🔧 运维关注点\n")
            lines.append(ops_tips)
            lines.append("")

        # 异常与边界情况（加处理建议）
        if api.get('exceptions'):
            lines.append("\n### ⚠️ 异常与边界情况\n")
            lines.append("> ⚠️ **注意**：如果遇到以下情况，按建议处理\n")
            lines.append(f"{api['exceptions']}\n")

        lines.append("---\n")

    return '\n'.join(lines)


def build_ops_tips_md(api: dict) -> str:
    """为新人版构建运维关注点 Markdown。"""
    tips = []
    http_method = api.get('http_method', '')
    http_path = api.get('http_path', '')

    if http_method == 'GET':
        tips.append(f"- `{http_path}` — 健康检查时可以调用此接口，是查询操作，幂等的，可以放心重试")

    if http_method == 'POST':
        tips.append(f"- `{http_path}` — 这是提交类操作，重复提交可能产生重复数据，请确认业务幂等性")

    if http_method in ('PUT', 'DELETE'):
        tips.append(f"- `{http_path}` — 修改/删除操作，调用前请确认，这类操作不可逆")

    if api.get('exceptions'):
        tips.append("- 异常处理参考上方说明")

    if not tips:
        return ""

    return '\n'.join(tips)


def main():
    parser = argparse.ArgumentParser(description='组装 Markdown 业务文档')
    parser.add_argument('--model', required=True, help='final_model.json 路径')
    parser.add_argument('--output', required=True, help='输出 Markdown 文件路径')
    parser.add_argument('--audience', default='technical', choices=['technical', 'newcomer'],
                        help='受众类型: technical (默认) 或 newcomer (产品经理/运维)')
    args = parser.parse_args()

    with open(args.model, 'r', encoding='utf-8') as f:
        model = json.load(f)

    if args.audience == 'newcomer':
        md = build_markdown_newcomer(model)
    else:
        md = build_markdown_technical(model)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(md)

    audience_label = '新人引导版' if args.audience == 'newcomer' else '技术版'
    print(f"✅ {audience_label} Markdown 文档已生成: {args.output}")
    print(f"   共 {len(model['apis'])} 个接口卡片，{model['success_count']} 个成功分析")


if __name__ == '__main__':
    main()