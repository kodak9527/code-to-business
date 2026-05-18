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

# 6 个部分的标题模式
SECTION_PATTERNS = [
    ('summary',     r'={3,}\s*业务概述\s*={3,}'),
    ('flow',        r'={3,}\s*业务流程\s*={3,}'),
    ('rules',       r'={3,}\s*关键业务规则\s*={3,}'),
    ('call_chain',  r'={3,}\s*调用时序\s*={3,}'),
    ('data_models', r'={3,}\s*数据模型\s*={3,}'),
    ('exceptions',  r'={3,}\s*异常[／/]边界情况\s*={3,}'),
]


def parse_sections(text: str) -> dict:
    """解析 markdown 中的 6 个部分。返回 {section_name: content}。"""
    result = {}
    positions = []

    for name, pattern in SECTION_PATTERNS:
        m = re.search(pattern, text)
        if m:
            positions.append((m.start(), m.end(), name))

    positions.sort()

    for i, (start, end, name) in enumerate(positions):
        if i + 1 < len(positions):
            next_start = positions[i + 1][0]
            content = text[end:next_start].strip()
        else:
            content = text[end:].strip()
        result[name] = content

    return result


def parse_flow(text: str) -> list:
    """解析业务流程为步骤列表。"""
    steps = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 匹配 "步骤N: ..." 或 "N. ..." 或 "N、..." 或 "- ..."
        m = re.match(r'(?:步骤\s*\d+[：:.]?\s*|\d+[.、)\s]\s*|[-*]\s*)(.+)', line)
        if m:
            steps.append(m.group(1).strip())
        elif line and not line.startswith('#'):
            # 非标题行，也当作步骤
            steps.append(line)
    return steps


def parse_rules(text: str) -> list:
    """解析业务规则为列表。"""
    rules = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # 去掉开头的 - * 或编号
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
    args = parser.parse_args()

    analyses_dir = Path(args.dir)
    if not analyses_dir.is_dir():
        print(f"❌ 目录不存在: {args.dir}", file=sys.stderr)
        sys.exit(1)

    # 读取 file_groups.json 获取每个 cluster 的元信息
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

    with open(args.output, 'w', encoding='utf-8') as out:
        for fpath in md_files:
            cluster_id = fpath.stem  # 文件名去掉 .md
            print(f"  解析: {cluster_id} ...", end=' ')

            cluster_meta = cluster_map.get(cluster_id)
            if not cluster_meta:
                print('⚠️  未在 file_groups.json 中找到，跳过')
                skipped_count += 1
                continue

            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()

            # 检查是否标记为失败
            if re.search(r'={3,}\s*状态[：:]\s*失败\s*={3,}', text):
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
    print(f"   输出: {args.output}")


if __name__ == '__main__':
    main()
