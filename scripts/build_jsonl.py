#!/usr/bin/env python3
"""
build_jsonl.py — 将 OpenCode 产出的单个分析 JSON 文件合并为 JSONL

用法:
  python3 build_jsonl.py --dir output/analyses --output output/analysis_results.jsonl

OpenCode 在 step 2 中为每个功能簇生成一个 JSON 文件，此脚本将它们合并为
aggregator.py 需要的 JSONL 格式（每行一个 JSON 对象）。
"""

import argparse, json, sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='合并分析 JSON 文件为 JSONL')
    parser.add_argument('--dir', required=True, help='存放单个分析 JSON 的目录')
    parser.add_argument('--output', required=True, help='输出 JSONL 文件路径')
    args = parser.parse_args()

    analyses_dir = Path(args.dir)
    if not analyses_dir.is_dir():
        print(f"❌ 目录不存在: {args.dir}", file=sys.stderr)
        sys.exit(1)

    json_files = sorted(analyses_dir.glob('*.json'))
    if not json_files:
        print(f"❌ 目录中没有 JSON 文件: {args.dir}", file=sys.stderr)
        sys.exit(1)

    count = 0
    skipped = 0

    with open(args.output, 'w', encoding='utf-8') as out:
        for fpath in json_files:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"⚠️  跳过 {fpath.name}: {e}", file=sys.stderr)
                skipped += 1
                continue

            # 校验必要字段
            if 'cluster_id' not in data:
                print(f"⚠️  跳过 {fpath.name}: 缺少 cluster_id", file=sys.stderr)
                skipped += 1
                continue

            out.write(json.dumps(data, ensure_ascii=False) + '\n')
            count += 1

    print(f"✅ 合并完成: {count} 条写入 {args.output}")
    if skipped:
        print(f"⚠️  {skipped} 个文件被跳过")


if __name__ == '__main__':
    main()
