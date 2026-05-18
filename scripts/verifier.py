#!/usr/bin/env python3
"""
verifier.py — 二次校验：把 LLM 的初次分析 + 原始代码发回去，让 LLM 自己挑错

用法（独立运行）:
  python3 verifier.py \
    --results analysis_results.jsonl \
    --groups file_groups.json \
    --config config.yaml \
    --output verified_results.jsonl

也可作为 llm_analyzer.py 的 --verify 模式内置调用。
"""

import argparse, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path


# ── 校验 Prompt ────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个严谨的代码审查专家。你的任务是对比原始 Java 代码和一份业务分析报告，找出分析中的错误、遗漏或编造的内容。

规则：
1. 逐项检查分析报告的每一部分
2. 只指出「确实有误」的地方，不要吹毛求疵
3. 用中文输出
4. 如果分析完全正确，直接说「无修正」"""


USER_PROMPT_TEMPLATE = """## 原始代码
{code_blocks}

## 之前的分析报告

### 业务概述
{summary}

### 业务流程
{flow}

### 关键业务规则
{rules}

### 调用时序
{call_chain}

### 数据模型
{data_models}

### 异常/边界情况
{exceptions}

## 审核要求
请逐项检查以上分析是否准确：

1. **业务概述**: 描述是否和代码逻辑一致？有没有说反、说漏的？
2. **业务流程**: 步骤顺序是否正确？有没有遗漏关键步骤？
3. **业务规则**: 每条规则是否都能在代码中找到明确对应的逻辑？有没有编造规则？
4. **调用时序**: 调用链路是否正确？类名和方法名是否匹配代码？
5. **数据模型**: 字段类型和含义是否准确？
6. **异常/边界**: 代码中实际存在的异常处理是否都被覆盖了？

## 输出格式

如果发现错误，请用以下格式逐条输出：

### 修正
- [错误类型: 概述错误/流程遗漏/规则编造/时序错误/模型错误/异常遗漏]
  原内容: "..."
  修正为: "..."
  原因: 简述为什么原内容有误

如果没有发现任何错误，请输出：

### 无修正
分析结果准确，代码与分析一致，无需修改。"""


def assemble_verification_prompt(result_entry: dict, cluster: dict) -> tuple:
    """
    组装校验 Prompt。
    result_entry: LLM 第一次分析的结果
    cluster: 原始功能簇信息（含文件路径）
    返回: (system_prompt, user_prompt)
    """
    parsed = result_entry.get('parsed', {})
    
    # 加载原始代码
    code_blocks = []
    for finfo in cluster.get('files', []):
        fpath = finfo['path']
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            content = f"// [无法读取: {fpath}]"
        code_blocks.append(f"### {finfo.get('class_name', fpath)} ({finfo.get('role', '')})\n```java\n{content}\n```")
    
    flow_text = '\n'.join(parsed.get('flow', []))
    rules_text = '\n'.join(f"- {r}" for r in parsed.get('rules', []))
    models_text = '\n'.join(f"- {m}" for m in parsed.get('data_models', []))
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        code_blocks='\n\n'.join(code_blocks),
        summary=parsed.get('summary', '(无)'),
        flow=flow_text or '(无)',
        rules=rules_text or '(无)',
        call_chain=parsed.get('call_chain', '(无)'),
        data_models=models_text or '(无)',
        exceptions=parsed.get('exceptions', '(无)'),
    )
    
    return SYSTEM_PROMPT, user_prompt


def call_llm(system_prompt: str, user_prompt: str, config: dict) -> dict:
    """调用内部 LLM API。"""
    llm_config = config['llm']
    base_url = llm_config['base_url'].rstrip('/')
    api_key = llm_config['api_key']
    model = llm_config['model']
    
    body = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'max_tokens': llm_config.get('max_tokens', 4096),
        'temperature': 0.2,  # 校验用低温度
    }
    
    data = json.dumps(body).encode('utf-8')
    url = f"{base_url}/chat/completions"
    
    req = urllib.request.Request(url, data=data)
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            return {'success': True, 'content': content}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def parse_verification(content: str) -> dict:
    """
    解析 LLM 校验输出。
    返回 {
        'passed': True/False,  # True = 无修正, False = 有修正
        'corrections': [...],  # 修正列表
        'raw': content,        # 原始输出
    }
    """
    # 检查是否通过
    if '无修正' in content and '### 修正' not in content:
        return {
            'passed': True,
            'corrections': [],
            'raw': content,
        }
    
    # 解析修正条目
    corrections = []
    # 匹配格式: - [错误类型: xxx] \n 原内容: "..." \n 修正为: "..." \n 原因: ...
    correction_blocks = re.split(r'\n(?=-\s*\[)', content)
    
    for block in correction_blocks:
        block = block.strip()
        if not block.startswith('- ['):
            continue
        
        error_type = ''
        original = ''
        corrected = ''
        reason = ''
        
        type_match = re.match(r'-\s*\[([^\]]+)\]', block)
        if type_match:
            error_type = type_match.group(1).strip()
        
        orig_match = re.search(r'原内容[：:]\s*["\"]?(.+?)["\"]?(?:\n|$)', block)
        if orig_match:
            original = orig_match.group(1).strip('"\' ').rstrip('"\' ')
        
        corr_match = re.search(r'修正为[：:]\s*["\"]?(.+?)["\"]?(?:\n|$)', block)
        if corr_match:
            corrected = corr_match.group(1).strip('"\' ').rstrip('"\' ')
        
        reason_match = re.search(r'原因[：:]\s*(.+?)(?:\n|$)', block)
        if reason_match:
            reason = reason_match.group(1).strip()
        
        corrections.append({
            'type': error_type,
            'original': original,
            'corrected': corrected,
            'reason': reason,
        })
    
    return {
        'passed': len(corrections) == 0,
        'corrections': corrections,
        'raw': content,
    }


def verify_results(results_path: str, groups_path: str, config: dict, output_path: str, dry_run: bool = False) -> dict:
    """
    对每条成功分析的结果进行二次校验。
    返回 stats 字典。
    """
    # 读取分组数据（需要原始代码）
    with open(groups_path, 'r', encoding='utf-8') as f:
        group_data = json.load(f)
    
    cluster_map = {c['id']: c for c in group_data['clusters']}
    
    # 读取分析结果
    results = []
    with open(results_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    
    rate_limit = config.get('llm', {}).get('rate_limit_rpm', 10)
    min_interval = 60.0 / rate_limit
    
    stats = {'total': 0, 'verified': 0, 'corrected': 0, 'failed': 0, 'skipped': 0}
    
    with open(output_path, 'w', encoding='utf-8') as out_f:
        for i, entry in enumerate(results):
            cid = entry['cluster_id']
            
            # 跳过失败的条目
            if not entry.get('success'):
                out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                stats['skipped'] += 1
                continue
            
            # 跳过 dry-run 条目
            if entry.get('error') == 'dry-run':
                out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                stats['skipped'] += 1
                continue
            
            stats['total'] += 1
            cluster = cluster_map.get(cid)
            
            if not cluster:
                print(f"   ⚠️  {cid}: 找不到对应的功能簇，跳过校验")
                entry['verified'] = False
                entry['verification_error'] = '找不到功能簇'
                out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                stats['failed'] += 1
                continue
            
            print(f"\n[{i + 1}/{len(results)}] 校验: {cid}")
            
            if dry_run:
                entry['verified'] = False
                entry['verification_note'] = 'dry-run: 校验已跳过'
                out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                stats['skipped'] += 1
                continue
            
            # 组装并发送校验 Prompt
            sys_prompt, user_prompt = assemble_verification_prompt(entry, cluster)
            llm_result = call_llm(sys_prompt, user_prompt, config)
            
            if llm_result['success']:
                verification = parse_verification(llm_result['content'])
                entry['verified'] = True
                entry['verification_passed'] = verification['passed']
                entry['corrections'] = verification['corrections']
                entry['verification_raw'] = verification['raw']
                
                if verification['passed']:
                    stats['verified'] += 1
                    print(f"   ✅ 校验通过（无修正）")
                else:
                    stats['corrected'] += 1
                    print(f"   🔧 发现 {len(verification['corrections'])} 处修正")
                    for c in verification['corrections']:
                        print(f"      - [{c['type']}] {c['original'][:50]}... → {c['corrected'][:50]}...")
            else:
                entry['verified'] = False
                entry['verification_error'] = llm_result['error']
                stats['failed'] += 1
                print(f"   ❌ 校验失败: {llm_result['error']}")
            
            out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            out_f.flush()
            
            # 速率限制
            if i < len(results) - 1:
                time.sleep(min_interval)
    
    return stats


# ── 主入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='二次校验 LLM 分析结果')
    parser.add_argument('--results', required=True, help='analysis_results.jsonl（LLM 第一次分析输出）')
    parser.add_argument('--groups', required=True, help='file_groups.json（功能簇分组，需要原始代码）')
    parser.add_argument('--config', required=True, help='config.yaml 路径')
    parser.add_argument('--output', required=True, help='输出 verified_results.jsonl')
    parser.add_argument('--dry-run', action='store_true', help='不调 LLM，只组装 prompt')
    args = parser.parse_args()
    
    # 读取配置
    try:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except ImportError:
        print("⚠️  未安装 PyYAML，尝试使用简易 YAML 解析...")
        # 手动解析（复用 llm_analyzer 的实现思路）
        with open(args.config, 'r') as f:
            content = f.read()
        config = {}
        current_section = None
        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if not line.startswith('  ') and ':' in stripped:
                key, val = stripped.split(':', 1)
                val = val.strip().strip('"').strip("'")
                if not val:
                    current_section = key
                else:
                    config[key] = val
            elif line.startswith('  ') and ':' in stripped:
                key, val = stripped.strip().split(':', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if current_section:
                    config.setdefault(current_section, {})[key] = val
    
    print("🔍 二次校验 LLM 分析结果...")
    
    stats = verify_results(args.results, args.groups, config, args.output, dry_run=args.dry_run)
    
    print(f"\n{'─' * 50}")
    print(f"📊 校验统计:")
    print(f"   总需校验: {stats['total']}")
    print(f"   ✅ 通过: {stats['verified']}")
    print(f"   🔧 有修正: {stats['corrected']}")
    print(f"   ❌ 校验失败: {stats['failed']}")
    print(f"   ⏭️ 跳过: {stats['skipped']}")
    print(f"📄 输出: {args.output}")


if __name__ == '__main__':
    main()
