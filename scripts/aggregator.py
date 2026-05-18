#!/usr/bin/env python3
"""
aggregator.py — 汇总 LLM 分析结果，生成 Mermaid 图表和最终数据模型

用法:
  python3 aggregator.py --results analysis_results.jsonl --output final_model.json
"""

import argparse, json, re, sys
from pathlib import Path


def parse_call_chain_text(text: str) -> dict:
    """
    从 LLM 输出的调用时序文本中解析结构，生成 Mermaid 时序图代码。
    
    输入示例:
      客户端 → OrderController.createOrder(OrderDTO)
        → OrderServiceImpl.createOrder(dto) — 创建订单
          → InventoryServiceImpl.deductStock(skuId, qty) — 扣减库存
          → OrderMapper.insert(order) — 插入数据库
        → 返回 Result<Long>(orderId) 给客户端
    
    输出: {"mermaid": "...", "participants": [...], "steps": [...]}
    """
    lines = text.strip().split('\n')
    
    # 提取参与者和调用步骤
    participants = {}
    steps = []
    
    # 解析缩进层级
    for line in lines:
        line = line.strip()
        if not line or not ('→' in line or '->' in line):
            continue
        
        # 处理 "客户端 → Controller.method(param) — 说明" 格式
        # 或 "Controller.method(param) — 说明"
        # 或 "→ 返回 xxx"
        
        indent = len(line) - len(line.lstrip())
        depth = indent // 2  # 粗略缩进深度
        
        # 分割箭头
        parts = re.split(r'\s*[→]\s*', line)
        
        if len(parts) == 2:
            caller_raw = parts[0].lstrip('→ ').strip()
            callee_raw = parts[1].strip()
        elif line.startswith('→') or line.startswith('->'):
            caller_raw = ''
            callee_raw = line.lstrip('→-> ').strip()
        else:
            continue
        
        # 解析被调用方（可能有 " — 说明" 后缀）
        callee_clean = callee_raw
        note = ''
        if ' — ' in callee_raw:
            callee_clean, note = callee_raw.split(' — ', 1)
        elif ' - ' in callee_raw:
            callee_clean, note = callee_raw.split(' - ', 1)
        
        # 提取类名和方法
        callee_class = ''
        callee_method = ''
        if '.' in callee_clean:
            callee_class, callee_method = callee_clean.rsplit('.', 1)
        
        # 清理 (param) 后缀
        callee_method = re.sub(r'\([^)]*\)', '()', callee_method).strip()
        
        # 合并类名
        callee_display = f"{callee_class}.{callee_method}" if callee_class else callee_clean
        
        # 注册参与者
        if callee_class and callee_class not in participants:
            participants[callee_class] = callee_class
        
        steps.append({
            'depth': depth,
            'caller': caller_raw.strip(),
            'callee': callee_display,
            'callee_class': callee_class,
            'note': note.strip(),
        })
    
    # 生成 Mermaid 时序图
    mermaid_lines = ['sequenceDiagram']
    mermaid_lines.append('    participant Client as 客户端/前端')
    
    # 按首次出现顺序列出参与者
    seen = {'Client'}
    for s in steps:
        if s['callee_class'] and s['callee_class'] not in seen:
            alias = (s['callee_class'][:1].upper() + s['callee_class'][1:]
                     if len(s['callee_class']) > 1 else s['callee_class'])
            if alias not in seen:
                mermaid_lines.append(f'    participant {alias} as {s["callee_class"]}')
                seen.add(alias)
                seen.add(s['callee_class'])
    
    # 生成调用箭头
    prev_class = 'Client'
    prev_alias = 'Client'
    
    # 建立 class → alias 映射
    class_to_alias = {'Client': 'Client'}
    for s in steps:
        if s['callee_class']:
            alias = (s['callee_class'][:1].upper() + s['callee_class'][1:]
                     if len(s['callee_class']) > 1 else s['callee_class'])
            class_to_alias[s['callee_class']] = alias
    
    for s in steps:
        callee_alias = class_to_alias.get(s['callee_class'], 'Unknown')
        callee_display = s['callee']
        note = f' — {s["note"]}' if s['note'] else ''
        
        # 判断箭头方向（如果 caller 是返回值场景）
        if '返回' in s['caller'].lower() or '返回' in s['callee'].lower():
            mermaid_lines.append(f'    {prev_alias}-->>{callee_alias}: {callee_display}{note}')
        else:
            mermaid_lines.append(f'    {prev_alias}->>{callee_alias}: {callee_display}{note}')
        
        prev_alias = callee_alias
    
    return {
        'mermaid': '\n'.join(mermaid_lines),
        'participants': list(participants.keys()),
        'steps': steps,
    }


def extract_flowchart_from_rules(rules: list, summary: str) -> str:
    """
    从业务规则和流程描述生成 Mermaid 流程图。
    如果规则中有明显的 if/else 分支，生成决策节点。
    """
    if not rules and not summary:
        return ''
    
    lines = ['flowchart TD']
    node_id = 0
    
    def next_id(prefix='N'):
        nonlocal node_id
        node_id += 1
        return f'{prefix}{node_id}'
    
    has_conditional = any(
        '如果' in r or '若' in r or '当' in r or '判断' in r or '检查' in r or '验证' in r
        for r in rules
    )
    
    if not has_conditional:
        lines.append(f'    {next_id()}[接收请求] --> {next_id()}[处理业务逻辑]')
        lines.append(f'    N{node_id} --> {next_id()}[返回结果]')
    else:
        lines.append(f'    {next_id()}[接收请求]')
        current = f'N{node_id}'
        
        for rule in rules:
            rid = next_id()
            if '如果' in rule or '若' in rule:
                yes_id = next_id()
                no_id = next_id()
                lines.append(f'    {current} --> {rid}{{{rule[:30]}...}}')
                lines.append(f'    {rid} -->|是| {yes_id}[继续]')
                lines.append(f'    {rid} -->|否| {no_id}[拒绝/异常]')
                current = yes_id
            else:
                lines.append(f'    {current} --> {rid}[{rule[:40]}]')
                current = rid
        
        lines.append(f'    {current} --> {next_id()}[返回结果]')
    
    return '\n'.join(lines)


def aggregate(results: list) -> dict:
    """汇总所有分析结果，生成最终数据模型。"""
    
    apis = []
    
    for entry in results:
        cid = entry.get('cluster_id', 'unknown')
        
        if not entry.get('success'):
            apis.append({
                'cluster_id': cid,
                'http_method': entry.get('http_method', 'N/A'),
                'http_path': entry.get('http_path', 'N/A'),
                'mode': entry.get('mode', 'deep'),
                'status': 'failed',
                'error': entry.get('error', 'Unknown error'),
                'verified': False,
            })
            continue
        
        parsed = entry['parsed']
        
        # 校验信息
        verification = entry.get('verification', {})
        verified = entry.get('verified', False)
        confidence = verification.get('confidence', 0)
        has_issues = bool(
            verification.get('hallucinations') or
            verification.get('omissions') or
            verification.get('call_chain_issues')
        )
        
        # 如果校验发现有修正建议，优先使用修正版
        corrected = verification.get('corrected_analysis', '')
        if corrected:
            # 用修正版覆盖原始分析
            from scripts.llm_analyzer import parse_llm_response
            corrected_parsed = parse_llm_response(corrected)
            if corrected_parsed.get('summary'):
                parsed = corrected_parsed
        
        call_chain_text = parsed.get('call_chain', '')
        
        # 生成 Mermaid 时序图
        mermaid_seq = parse_call_chain_text(call_chain_text) if call_chain_text else {}
        
        # 生成 Mermaid 流程图
        mermaid_flow = extract_flowchart_from_rules(
            parsed.get('rules', []),
            parsed.get('summary', '')
        )
        
        # 校验标签
        verify_badge = ''
        if verified:
            if has_issues or confidence < 60:
                verify_badge = '⚠️ 低可信度' if confidence < 60 else '⚠️ 存疑'
            else:
                verify_badge = '✅ 已校验'
        else:
            verify_badge = '⏳ 未校验'
        
        api_info = {
            'cluster_id': entry['cluster_id'],
            'mode': entry.get('mode', 'deep'),
            'http_method': entry.get('http_method', 'N/A'),
            'http_path': entry.get('http_path', 'N/A'),
            'entry_class': entry.get('entry_class', ''),
            'entry_method': entry.get('entry_method', ''),
            'endpoints': entry.get('endpoints', []),
            'status': 'success',
            # 业务描述
            'summary': parsed.get('summary', ''),
            'flow': parsed.get('flow', []),
            'rules': parsed.get('rules', []),
            'exceptions': parsed.get('exceptions', ''),
            'data_models': parsed.get('data_models', []),
            # 图表
            'sequence_diagram': mermaid_seq.get('mermaid', ''),
            'flowchart_diagram': mermaid_flow,
            # 调试
            'call_chain_raw': call_chain_text,
            # 校验结果（透传）
            'verified': entry.get('verified'),
            'verification_passed': entry.get('verification_passed'),
            'corrections': entry.get('corrections', []),
        }
        apis.append(api_info)
    
    return {
        'total_apis': len(apis),
        'success_count': sum(1 for a in apis if a['status'] == 'success'),
        'fail_count': sum(1 for a in apis if a['status'] == 'failed'),
        'apis': apis,
    }


def main():
    parser = argparse.ArgumentParser(description='汇总 LLM 分析结果')
    parser.add_argument('--results', required=True, help='analysis_results.jsonl 路径')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    args = parser.parse_args()
    
    results = []
    with open(args.results, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    
    print(f"📊 汇总 {len(results)} 条分析结果...")
    
    model = aggregate(results)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(model, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 最终数据模型: {args.output}")
    print(f"   成功: {model['success_count']}, 失败: {model['fail_count']}")


if __name__ == '__main__':
    main()
