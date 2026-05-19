#!/usr/bin/env python3
"""
parse_analysis.py — 将 OpenCode 产出的 markdown 分析文件解析为 JSONL

用法:
  python3 parse_analysis.py --dir output/analyses --groups output/file_groups.json --output output/analysis_results.jsonl

输入: 每个功能簇一个 .md 文件，格式为 6 部分 markdown
输出: analysis_results.jsonl（aggregator.py 直接消费）
"""

import argparse, json, re, sys
from pathlib import Path

# 每个部分的多种标题变体（按优先级尝试匹配）
SECTION_PATTERNS = {
    'summary': [
        r'={3,}\s*业务概述\s*={3,}',
        r'业务概述[：:\s]+',
        r'【业务概述】',
        r'#\s*业务概述',
    ],
    'flow': [
        r'={3,}\s*业务流程\s*={3,}',
        r'业务流程[：:\s]+',
        r'【业务流程】',
        r'#\s*业务流程',
    ],
    'rules': [
        r'={3,}\s*关键业务规则\s*={3,}',
        r'关键业务规则[：:\s]+',
        r'【关键业务规则】',
        r'#\s*关键业务规则',
    ],
    'call_chain': [
        r'={3,}\s*调用时序\s*={3,}',
        r'调用时序[：:\s]+',
        r'【调用时序】',
        r'#\s*调用时序',
    ],
    'data_models': [
        r'={3,}\s*数据模型\s*={3,}',
        r'数据模型[：:\s]+',
        r'【数据模型】',
        r'#\s*数据模型',
    ],
    'exceptions': [
        r'={3,}\s*异常[／/]?\s*边界情况\s*={3,}',
        r'异常[／/]?\s*边界情况[：:\s]+',
        r'【异常[／/]?边界情况】',
        r'#\s*异常[／/]?\s*边界情况',
    ],
}


def parse_sections(text: str) -> dict:
    """
    解析 markdown 中的 6 个部分。支持标题的多种变体格式。
    返回 {section_name: content}，缺失的部分返回空字符串。
    """
    result = {}
    positions = []

    for name, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                positions.append((m.start(), m.end(), name))
                break

    positions.sort()

    for i, (start, end, name) in enumerate(positions):
        if i + 1 < len(positions):
            next_start = positions[i + 1][0]
            content = text[end:next_start].strip()
        else:
            content = text[end:].strip()
        result[name] = content

    # 确保所有 6 个部分都存在，缺失的返回空
    for name in SECTION_PATTERNS:
        if name not in result:
            result[name] = ''

    return result


def validate_sections(sections: dict, cluster_id: str) -> list:
    """
    检查解析出的 sections 是否有空内容。
    返回警告信息列表。
    """
    warnings = []
    required = ['summary', 'flow', 'call_chain']
    recommended = ['rules', 'data_models', 'exceptions']

    for name in required:
        if not sections.get(name):
            warnings.append(f"[{cluster_id}] 必填部分「{name}」解析结果为空")

    for name in recommended:
        if not sections.get(name):
            warnings.append(f"[{cluster_id}] 建议部分「{name}」解析结果为空")

    return warnings


def parse_flow(text: str) -> list:
    """解析业务流程为步骤列表。"""
    steps = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 匹配 "步骤N: ..." / "N. ..." / "N、..." / "- ..."
        m = re.match(r'(?:步骤\s*\d+[：:.、]?\s*|\d+[.、)\s]\s*|[-*]\s*)(.+)', line)
        if m:
            steps.append(m.group(1).strip())
        elif line and not line.startswith('#'):
            steps.append(line)
    return steps


def parse_rules(text: str) -> list:
    """解析业务规则为列表。"""
    rules = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        cleaned = re.sub(r'^[-*]\s*|\d+[.、)]\s*', '', line).strip()
        if cleaned and '无明显业务规则' not in cleaned:
            rules.append(cleaned)
    return rules


def parse_data_models(text: str) -> list:
    """解析数据模型列表。"""
    models = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        cleaned = re.sub(r'^[-*]\s*', '', line).strip()
        if cleaned:
            models.append(cleaned)
    return models


def main():
    parser = argparse.ArgumentParser(description='解析 markdown 分析文件为 JSONL')
    parser.add_argument('--dir', required=True, help='分析 markdown 文件目录')
    parser.add_argument('--groups', required=True, help='file_groups.json 路径')
    parser.add_argument('--output', required=True, help='输出 JSONL 路径')
    parser.add_argument('--strict', action='store_true', help='有空 section 时退出码非 0')
    args = parser.parse_args()

    analyses_dir = Path(args.dir)
    if not analyses_dir.is_dir():
        print(f"❌ 目录不存在: {args.dir}", file=sys.stderr)
        sys.exit(1)

    with open(args.groups, 'r', encoding='utf-8') as f:
        groups_data = json.load(f)

    clusters = groups_data.get('clusters', [])
    cluster_map = {c['cluster_id']: c for c in clusters}

    md_files = sorted(analyses_dir.glob('*.md'))
    if not md_files:
        print(f"❌ 目录中没有 .md 文件: {args.dir}", file=sys.stderr)
        sys.exit(1)

    success_count = 0
    fail_count = 0
    skipped_count = 0
    all_warnings = []

    with open(args.output, 'w', encoding='utf-8') as out:
        for fpath in md_files:
            cluster_id = fpath.stem
            print(f"  解析: {cluster_id} ...", end=' ')

            cluster_meta = cluster_map.get(cluster_id)
            if not cluster_meta:
                print('⚠️  未在 file_groups.json 中找到，跳过')
                skipped_count += 1
                continue

            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()

            # 检查是否标记为失败
            if re.search(r'={3,}\s*状态[：:]\s*失败\s*={3,}', text, re.IGNORECASE):
                fail_match = re.search(r'状态[：:]\s*失败\s*={3,}\s*\n?(.+)', text, re.DOTALL)
                error_msg = fail_match.group(1).strip()[:200] if fail_match else '分析失败'
                entry = {
                    'cluster_id': cluster_id,
                    'mode': cluster_meta.get('mode', 'deep'),
                    'http_method': cluster_meta.get('http_method', 'N/A'),
                    'http_path': cluster_meta.get('http_path', 'N/A'),
                    'entry_class': cluster_meta.get('entry_class', ''),
                    'entry_method': cluster_meta.get('entry_method', ''),
                    'endpoints': cluster_meta.get('endpoints', []),
                    'success': False,
                    'error': error_msg,
                }
                out.write(json.dumps(entry, ensure_ascii=False) + '\n')
                print('⚠️  标记为失败')
                fail_count += 1
                continue

            # 解析 6 个部分
            sections = parse_sections(text)

            # 校验空 section
            warnings = validate_sections(sections, cluster_id)
            all_warnings.extend(warnings)

            summary = sections.get('summary', '')
            flow_text = sections.get('flow', '')
            rules_text = sections.get('rules', '')
            call_chain = sections.get('call_chain', '')
            data_models_text = sections.get('data_models', '')
            exceptions = sections.get('exceptions', '')

            flow = parse_flow(flow_text)
            rules = parse_rules(rules_text)
            data_models = parse_data_models(data_models_text)

            entry = {
                'cluster_id': cluster_id,
                'mode': cluster_meta.get('mode', 'deep'),
                'http_method': cluster_meta.get('http_method', 'N/A'),
                'http_path': cluster_meta.get('http_path', 'N/A'),
                'entry_class': cluster_meta.get('entry_class', ''),
                'entry_method': cluster_meta.get('entry_method', ''),
                'endpoints': cluster_meta.get('endpoints', []),
                'success': True,
                'parsed': {
                    'summary': summary,
                    'flow': flow,
                    'rules': rules,
                    'exceptions': exceptions,
                    'data_models': data_models,
                    'call_chain': call_chain,
                },
                'verified': False,
            }
            out.write(json.dumps(entry, ensure_ascii=False) + '\n')
            print('✅')
            success_count += 1

    print(f"\n📊 解析完成: {success_count} 成功, {fail_count} 失败, {skipped_count} 跳过")

    if all_warnings:
        print(f"\n⚠️  空 section 警告 ({len(all_warnings)} 条):")
        for w in all_warnings[:10]:
            print(f"   {w}")
        if len(all_warnings) > 10:
            print(f"   ... 还有 {len(all_warnings) - 10} 条")

    if all_warnings and args.strict:
        print("\n❌ strict 模式：有空 section，退出码 1")
        sys.exit(1)

    print(f"   输出: {args.output}")


if __name__ == '__main__':
    main()