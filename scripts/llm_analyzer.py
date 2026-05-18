#!/usr/bin/env python3
"""
llm_analyzer.py — 调用内部 LLM 分析 Java 功能簇

用法:
  python3 llm_analyzer.py \
    --groups file_groups.json \
    --config config.yaml \
    --output analysis_results.jsonl

依赖: 内部 LLM 必须提供 OpenAI 兼容 API
"""

import argparse, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path


# ── Prompt 模板（会填入代码后发送给 LLM）─────────────────────

SYSTEM_PROMPT = """你是一个电商业务分析专家。你的任务是把 Java 代码翻译成不懂技术的运营人员也能看懂的业务文档。

规则：
1. 用中文输出
2. 从「用户视角」描述业务——用户点击了什么，系统做了什么，最终返回了什么
3. 不要复述代码，不要用「该方法调用了 xxxService」这种说法
4. 不要编造代码中没有的业务规则
5. 严格按照指定的 6 个部分输出"""


USER_PROMPT_TEMPLATE = """## 任务
请阅读以下 Java 代码，分析 {entry_desc} 的完整业务逻辑。

## 代码
{code_blocks}

## 输出要求
请严格按照以下 6 个部分输出，每部分用 3 个等号包裹的标题分隔：

=== 业务概述 ===
用一段话（100-200字）描述这个接口/功能「从用户视角」做了什么。用大白话。

=== 业务流程 ===
分步骤描述完整流程，每一步格式：
步骤N: 做什么 → 得到什么结果

=== 关键业务规则 ===
- 规则1: xxx
- 规则2: xxx
只列出代码中明确体现的规则。没有则写「无明显业务规则」。

=== 调用时序 ===
用缩进箭头描述调用链路，格式：
客户端 → ControllerName.methodName(参数)
  → ServiceName.methodName(参数) — 简述这一步做了什么
    → MapperName.methodName(参数) — 操作了什么数据
  → 返回什么结果给客户端

注意：每一步都要写清楚参数含义和返回值含义。

=== 数据模型 ===
列出涉及的主要数据结构：
- ClassName: 用途简述
  - fieldName (Type): 字段含义

=== 异常/边界情况 ===
代码中处理了哪些异常或边界情况？（如参数校验、库存不足、重复提交等）
没有则写「无特殊异常处理」"""


def assemble_prompt(cluster: dict, index: dict) -> tuple:
    """组装发给 LLM 的 Prompt。返回 (system_prompt, user_prompt, estimated_tokens)。"""
    
    # 构建代码块
    code_blocks = []
    total_chars = 0
    for finfo in cluster['files']:
        fpath = finfo['path']
        content = index.get(fpath, '')
        if not content:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = f"// [无法读取: {fpath}]"
        
        code_blocks.append(f"### {finfo['class_name']} ({finfo['role']}) — {fpath}\n```java\n{content}\n```")
        total_chars += len(content)
    
    # 入口描述
    if cluster['mode'] == 'deep':
        entry_desc = f"接口 **{cluster['http_method']} {cluster['http_path']}** ({cluster['entry_class']}.{cluster['entry_method']})"
    else:
        eps = cluster.get('endpoints', [])
        ep_list = '\n'.join(f"- {e['http_method']} {e['path']} ({e['method']})" for e in eps)
        entry_desc = f"模块 **{cluster['entry_class']}**，包含以下接口：\n{ep_list}"
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        entry_desc=entry_desc,
        code_blocks='\n\n'.join(code_blocks),
    )
    
    estimated_tokens = total_chars // 3  # 粗略估算
    
    return SYSTEM_PROMPT, user_prompt, estimated_tokens


def call_llm(system_prompt: str, user_prompt: str, config: dict) -> dict:
    """调用内部 LLM API。返回 {"success": True/False, "content": "...", "error": "..."}"""
    
    llm_config = config['llm']
    base_url = llm_config['base_url'].rstrip('/')
    api_key = llm_config['api_key']
    model = llm_config['model']
    max_tokens = llm_config.get('max_tokens', 4096)
    temperature = llm_config.get('temperature', 0.3)
    
    url = f"{base_url}/chat/completions"
    
    body = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'max_tokens': max_tokens,
        'temperature': temperature,
    }
    
    data = json.dumps(body).encode('utf-8')
    
    req = urllib.request.Request(url, data=data)
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            return {'success': True, 'content': content}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        return {'success': False, 'error': f"HTTP {e.code}: {error_body[:500]}"}
    except urllib.error.URLError as e:
        return {'success': False, 'error': f"连接失败: {e.reason}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def parse_llm_response(content: str) -> dict:
    """解析 LLM 返回的 6 部分结构化内容。"""
    result = {
        'summary': '',       # 业务概述
        'flow': [],          # 业务流程
        'rules': [],         # 关键业务规则
        'call_chain': '',    # 调用时序（原始文本）
        'data_models': [],   # 数据模型
        'exceptions': '',    # 异常/边界情况
        'raw': content,      # 原始输出（备用）
    }
    
    # 按 === xxx === 分割
    sections = re.split(r'===\s*(.+?)\s*===', content)
    
    # sections[0] = 开头被丢弃的内容（如果有）
    # sections[1] = 标题1, sections[2] = 内容1, sections[3] = 标题2, ...
    for i in range(1, len(sections), 2):
        title = sections[i].strip()
        body = sections[i + 1].strip() if i + 1 < len(sections) else ''
        
        if '业务概述' in title:
            result['summary'] = body
        elif '业务流程' in title:
            result['flow'] = [s.strip() for s in body.split('\n') if s.strip() and not s.strip().startswith('#')]
        elif '关键业务规则' in title or '业务规则' in title:
            result['rules'] = [s.strip().lstrip('- ') for s in body.split('\n') if s.strip().startswith('-')]
        elif '调用时序' in title:
            result['call_chain'] = body
        elif '数据模型' in title:
            result['data_models'] = [s.strip().lstrip('- ') for s in body.split('\n') if s.strip().startswith('-')]
        elif '异常' in title or '边界' in title:
            result['exceptions'] = body
    
    # 如果没解析出任何结构化内容，把整个回复放进 summary
    if not result['summary'] and not result['flow']:
        result['summary'] = content
    
    return result


def load_file_contents(cluster: dict) -> dict:
    """加载功能簇中所有文件的内容。"""
    index = {}
    for finfo in cluster['files']:
        try:
            with open(finfo['path'], 'r', encoding='utf-8') as f:
                index[finfo['path']] = f.read()
        except Exception as e:
            index[finfo['path']] = f"// [读取失败: {e}]"
    return index


# ── 主入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='调用内部 LLM 分析 Java 功能簇')
    parser.add_argument('--groups', required=True, help='file_groups.json 路径')
    parser.add_argument('--config', required=True, help='config.yaml 路径')
    parser.add_argument('--output', required=True, help='输出 JSONL 文件路径')
    parser.add_argument('--dry-run', action='store_true', help='只输出 prompt 不调 LLM')
    parser.add_argument('--verify', action='store_true', help='分析完成后自动进行二次校验')
    parser.add_argument('--groups-file', help='file_groups.json（--verify 时需要，用于读取原始代码）')
    args = parser.parse_args()
    
    # 读取配置
    try:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except ImportError:
        print("⚠️  未安装 PyYAML，尝试使用简易 YAML 解析...")
        config = _parse_simple_yaml(args.config)
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {args.config}")
        print("   请从 config.example.yaml 复制并填写 config.yaml")
        sys.exit(1)
    
    # 读取分组
    with open(args.groups, 'r', encoding='utf-8') as f:
        group_data = json.load(f)
    
    clusters = group_data['clusters']
    total = len(clusters)
    print(f"📦 共 {total} 个功能簇待分析")
    
    rate_limit = config.get('llm', {}).get('rate_limit_rpm', 10)
    min_interval = 60.0 / rate_limit  # 请求最小间隔（秒）
    
    results = []
    success_count = 0
    fail_count = 0
    
    with open(args.output, 'w', encoding='utf-8') as out_f:
        for i, cluster in enumerate(clusters):
            cid = cluster['id']
            print(f"\n[{i + 1}/{total}] 分析: {cid}")
            
            # 组装 Prompt
            file_index = load_file_contents(cluster)
            sys_prompt, user_prompt, est_tokens = assemble_prompt(cluster, file_index)
            print(f"   文件数: {len(cluster['files'])}, 估算 tokens: ~{est_tokens}")
            
            if args.dry_run:
                # 只保存 prompt 不调 LLM
                prompt_file = f"/tmp/jbd_prompt_{cid}.txt"
                with open(prompt_file, 'w', encoding='utf-8') as pf:
                    pf.write(f"SYSTEM:\n{sys_prompt}\n\nUSER:\n{user_prompt}")
                result_entry = {
                    'cluster_id': cid,
                    'mode': cluster['mode'],
                    'http_method': cluster.get('http_method', 'N/A'),
                    'http_path': cluster.get('http_path', 'N/A'),
                    'success': False,
                    'error': 'dry-run',
                    'prompt_file': prompt_file,
                    'parsed': {},
                }
            else:
                # 调用 LLM
                llm_result = call_llm(sys_prompt, user_prompt, config)
                
                if llm_result['success']:
                    parsed = parse_llm_response(llm_result['content'])
                    result_entry = {
                        'cluster_id': cid,
                        'mode': cluster['mode'],
                        'http_method': cluster.get('http_method', 'N/A'),
                        'http_path': cluster.get('http_path', 'N/A'),
                        'entry_class': cluster['entry_class'],
                        'entry_method': cluster.get('entry_method'),
                        'endpoints': cluster.get('endpoints', []),
                        'success': True,
                        'parsed': parsed,
                    }
                    success_count += 1
                    print(f"   ✅ 成功 (输出 {len(llm_result['content'])} 字符)")
                else:
                    result_entry = {
                        'cluster_id': cid,
                        'mode': cluster['mode'],
                        'http_method': cluster.get('http_method', 'N/A'),
                        'http_path': cluster.get('http_path', 'N/A'),
                        'success': False,
                        'error': llm_result['error'],
                        'parsed': {},
                    }
                    fail_count += 1
                    print(f"   ❌ 失败: {llm_result['error']}")
            
            results.append(result_entry)
            out_f.write(json.dumps(result_entry, ensure_ascii=False) + '\n')
            out_f.flush()
            
            # 速率限制
            if not args.dry_run and i < total - 1:
                time.sleep(min_interval)
    
    print(f"\n{'─' * 50}")
    print(f"✅ 完成: {success_count} 成功, {fail_count} 失败 (共 {total})")
    print(f"📄 输出: {args.output}")
    
    # ── 自动二次校验 ──
    if args.verify and not args.dry_run:
        groups_file = args.groups_file or args.groups
        from pathlib import Path
        skill_dir = Path(__file__).resolve().parent.parent
        
        # 动态加载 verifier
        import importlib.util
        verifier_path = skill_dir / 'scripts' / 'verifier.py'
        spec = importlib.util.spec_from_file_location('verifier', verifier_path)
        verifier_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier_mod)
        
        verified_output = args.output.replace('.jsonl', '_verified.jsonl')
        print(f"\n🔍 开始二次校验...")
        
        verifier_mod.verify_results(
            args.output,
            groups_file,
            config,
            verified_output,
            dry_run=False,
        )
        
        print(f"✅ 校验后结果: {verified_output}")


def _parse_simple_yaml(path: str) -> dict:
    """简易 YAML 解析（PyYAML 不可用时的回退方案）。只支持简单嵌套。"""
    with open(path, 'r') as f:
        content = f.read()
    
    config = {}
    current_section = None
    current_sub = None
    
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        if line.startswith('  '):
            # 二级属性
            if ':' in stripped:
                key, val = stripped.split(':', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if current_sub is not None:
                    config.setdefault(current_section, {}).setdefault(current_sub, {})[key] = _coerce(val)
                else:
                    config.setdefault(current_section, {})[key] = _coerce(val)
        else:
            # 一级标题
            if ':' in stripped and not stripped.startswith('-'):
                key, val = stripped.split(':', 1)
                key = key.strip()
                val = val.strip()
                if not val:
                    current_section = key
                    current_sub = None
                else:
                    config[key] = _coerce(val.strip('"').strip("'"))
    
    return config


def _coerce(val: str):
    """尝试将字符串转为数字/布尔。"""
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


if __name__ == '__main__':
    main()
