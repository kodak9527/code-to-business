#!/usr/bin/env python3
"""
collector.py — Java 代码收集与功能簇分组

用法:
  python3 collector.py --target /path/to/project --mode deep --output file_groups.json
  python3 collector.py --target /path/to/project --mode overview --output file_groups.json
  python3 collector.py --target /path/to/SomeController.java --mode deep --output file_groups.json

输入:  Java 项目目录或单个文件
输出:  file_groups.json — 按功能簇分组的文件列表，供 llm_analyzer.py 消费
"""

import argparse, json, os, re, sys
from pathlib import Path
from collections import defaultdict


# ── 文件类型识别 ──────────────────────────────────────────

# 类级别注解 → 文件角色
ROLE_PATTERNS = [
    (r'@RestController', 'controller'),
    (r'@Controller(?!Advice)', 'controller'),
    (r'@Service', 'service'),
    (r'@Repository', 'repository'),
    (r'@Mapper\b', 'repository'),          # MyBatis
    (r'@FeignClient', 'feign_client'),
    (r'@Component', 'component'),
]


def classify_file(content: str) -> str:
    """根据内容判断文件角色。"""
    roles = []
    for pat, role in ROLE_PATTERNS:
        if re.search(pat, content):
            roles.append(role)
    
    if roles:
        return roles[0]  # 主角色取第一个匹配
    
    # 没有典型注解 → 看是否是纯数据类
    if re.search(r'class\s+\w+\s*\{', content) and _is_data_class(content):
        return 'model'
    
    return 'other'


def _is_data_class(content: str) -> bool:
    """判断是否是 DTO/Entity/VO 等数据类（只有字段+getter/setter，没有复杂逻辑）。"""
    # 简单判断：没有 @Service/@Repository 等注解，且主要是字段定义
    method_count = len(re.findall(r'(?:public|private|protected)\s+(?:\w[\w<>\[\],\s]+\s+)\w+\s*\([^)]*\)\s*(?:throws\s+\w+(?:\s*,\s*\w+)*)?\s*\{', content))
    field_count = len(re.findall(r'private\s+\w[\w<>\[\],\s]+\s+\w+\s*;', content))
    return field_count >= 2 and method_count <= 10


# ── 注解/方法提取 ──────────────────────────────────────────

def extract_class_annotations(content: str) -> list:
    """提取类级别注解。"""
    # 找到 class 声明之前的内容
    class_pos = re.search(r'\bclass\s+\w+', content)
    if not class_pos:
        return []
    prelude = content[:class_pos.start()]
    annotations = re.findall(r'@(\w+)(?:\([^)]*\))?', prelude)
    return annotations


def extract_http_mappings(content: str) -> list:
    """提取 HTTP 映射信息。"""
    results = []
    
    # @GetMapping("/path") / @PostMapping("/path") 等
    for m in re.finditer(r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', content):
        results.append({
            'http_method': m.group(1).upper(),
            'path': m.group(2),
            'annotation_start': m.start(),
        })
    
    # @RequestMapping(method = RequestMethod.GET, value = "/path")
    for m in re.finditer(
        r'@RequestMapping\s*\([^)]*method\s*=\s*(?:RequestMethod\.)?(\w+)[^)]*value\s*=\s*["\']([^"\']+)["\']',
        content):
        results.append({
            'http_method': m.group(1).upper(),
            'path': m.group(2),
            'annotation_start': m.start(),
        })
    
    return results


def extract_methods(content: str) -> list:
    """提取所有 public 方法。返回 [(method_name, start_pos, end_pos, annotations, param_str, return_type), ...]"""
    methods = []
    
    # 匹配方法签名（public/protected/private 可选）
    method_pat = re.compile(
        r'(?:public|protected|private)\s+'
        r'(?:static\s+)?'
        r'(?:synchronized\s+)?'
        r'([\w<>\[\],\s]+?)\s+'            # 返回类型
        r'(\w+)\s*'                         # 方法名
        r'\(([^)]*)\)',                     # 参数列表
    )
    
    for m in method_pat.finditer(content):
        method_name = m.group(2)
        return_type = m.group(1).strip()
        param_str = m.group(3)
        start = m.start()
        
        # 跳过接口中的抽象方法（没有方法体）
        body_start = content.find('{', m.end())
        if body_start == -1:
            continue
        
        # 跳过紧跟的 ';' 情况（接口/抽象方法）
        snippet = content[m.end():body_start].strip()
        if ';' in snippet.split('\n')[0] if '\n' in snippet else ';' in snippet:
            continue
        
        # 找方法体结束位置
        body_end = _find_matching_brace(content, body_start)
        if body_end == -1:
            continue
        
        # 提取方法前的注解
        pre_method = content[max(0, start - 500):start]
        annotations = _extract_method_annotations(pre_method)
        
        # 确定此方法属于哪个 HTTP mapping（找方法签名上方最近的）
        http_info = None
        closest_dist = float('inf')
        for hm in extract_http_mappings(content):
            # HTTP mapping 注解必须在方法签名之前
            if hm['annotation_start'] < start:
                dist = start - hm['annotation_start']
                if dist < closest_dist:
                    closest_dist = dist
                    http_info = hm
        
        methods.append({
            'name': method_name,
            'return_type': return_type,
            'params': param_str,
            'start': start,
            'end': body_end,
            'annotations': annotations,
            'http_mapping': http_info,
            'body': content[body_start:body_end + 1],  # 方法体（含花括号）
        })
    
    return methods


def _extract_method_annotations(pre_method: str) -> list:
    """从方法前的文本中提取注解。"""
    lines = pre_method.split('\n')
    annotations = []
    for line in reversed(lines):
        m = re.match(r'\s*@(\w+)', line.strip())
        if m:
            annotations.insert(0, m.group(1))
        elif line.strip() and not line.strip().startswith('//') and not line.strip().startswith('/*') and not line.strip().startswith('*'):
            break  # 遇到非注解非注释行就停
    return annotations


def _find_matching_brace(text: str, open_pos: int) -> int:
    """从 open_pos（花括号位置）找到匹配的闭合花括号。"""
    depth = 0
    i = open_pos
    while i < len(text):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


# ── 依赖注入字段提取 ───────────────────────────────────────

def extract_autowired_fields(content: str) -> list:
    """提取 @Autowired / @Resource 注入的字段。返回 [(field_name, type_name), ...]"""
    fields = []
    
    # 匹配模式：
    # @Autowired
    # private SomeService someService;
    # 或
    # @Resource
    # private SomeService someService;
    
    # 策略：找到注解，然后向下找字段声明
    for m in re.finditer(r'@(?:Autowired|Resource)(?:\([^)]*\))?', content):
        after = content[m.end():m.end() + 300]
        field_match = re.search(
            r'private\s+(\w[\w<>\[\],\s]*?)\s+(\w+)\s*;',
            after,
            re.DOTALL
        )
        if field_match:
            type_name = field_match.group(1).strip()
            field_name = field_match.group(2)
            fields.append({
                'field_name': field_name,
                'type_name': type_name,
            })
    
    return fields


def extract_method_calls(method_body: str) -> list:
    """从方法体中提取对其他对象的方法调用。"""
    calls = []
    # 匹配 objectName.methodName( 模式
    for m in re.finditer(r'(?:this\.)?(\w+)\.(\w+)\s*\(', method_body):
        obj_name = m.group(1)
        method_name = m.group(2)
        # 跳过常见的 Java 关键字和工具调用
        if obj_name in ('new', 'super', 'return', 'if', 'for', 'while', 'throw',
                        'System', 'String', 'Integer', 'Long', 'Boolean', 'Objects',
                        'Collections', 'List', 'Map', 'Set', 'Optional', 'Stream',
                        'StringUtils', 'BeanUtils', 'CollectionUtils', 'log', 'logger',
                        'Assert', 'Validator'):
            continue
        calls.append({
            'target': obj_name,
            'method': method_name,
        })
    return calls


# ── 文件扫描与索引 ─────────────────────────────────────────

def scan_java_files(target: str) -> list:
    """扫描目标路径下所有 .java 文件。"""
    target_path = Path(target).resolve()
    
    if target_path.is_file():
        return [str(target_path)]
    
    java_files = []
    for f in target_path.rglob('*.java'):
        # 跳过测试目录
        if '/test/' in str(f) or str(f).endswith('Test.java') or str(f).endswith('Tests.java'):
            continue
        java_files.append(str(f))
    
    return sorted(java_files)


def build_file_index(java_files: list) -> dict:
    """构建文件索引：文件名 → {path, content, role, class_name, methods, fields}"""
    index = {}
    
    for fpath in java_files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️  无法读取 {fpath}: {e}", file=sys.stderr)
            continue
        
        role = classify_file(content)
        class_name = _extract_class_name(content)
        package = _extract_package(content)
        
        index[fpath] = {
            'path': fpath,
            'content': content,
            'role': role,
            'class_name': class_name,
            'package': package,
            'full_class_name': f"{package}.{class_name}" if package else class_name,
            'methods': extract_methods(content) if role in ('controller', 'service') else [],
            'autowired_fields': extract_autowired_fields(content) if role in ('controller', 'service') else [],
        }
    
    # 构建 类型名 → 文件路径 的反向索引
    type_to_path = {}
    for fpath, info in index.items():
        if info['full_class_name']:
            type_to_path[info['full_class_name']] = fpath
            # 也加上简单类名（可能重名，后出现的覆盖）
            type_to_path[info['class_name']] = fpath
    
    return index, type_to_path


def _extract_class_name(content: str) -> str:
    """提取类名。"""
    m = re.search(r'(?:class|interface|enum)\s+(\w+)', content)
    return m.group(1) if m else 'Unknown'


def _extract_package(content: str) -> str:
    """提取包名。"""
    m = re.search(r'package\s+([\w.]+)\s*;', content)
    return m.group(1) if m else ''


# ── 功能簇构建 ────────────────────────────────────────────

def build_clusters(index: dict, type_to_path: dict, mode: str) -> list:
    """构建功能簇。"""
    clusters = []
    
    controller_files = {p: info for p, info in index.items() if info['role'] == 'controller'}
    
    for cpath, cinfo in controller_files.items():
        if mode == 'deep':
            # 模式 A: 每个 Controller 方法一个簇
            for method in cinfo['methods']:
                cluster = _build_single_cluster(
                    cpath, cinfo, method, index, type_to_path
                )
                if cluster:
                    clusters.append(cluster)
        else:
            # 模式 B: 整个 Controller 一个簇
            cluster = _build_controller_cluster(cpath, cinfo, index, type_to_path)
            if cluster:
                clusters.append(cluster)
    
    return clusters


def _build_single_cluster(controller_path: str, cinfo: dict, method: dict,
                          index: dict, type_to_path: dict) -> dict:
    """为单个 Controller 方法构建功能簇。"""
    files_to_include = {controller_path}
    call_chain = []
    
    # 从方法体的调用中追踪依赖
    if method.get('body'):
        calls = extract_method_calls(method['body'])
        _resolve_dependencies(
            calls, cinfo['autowired_fields'], index, type_to_path,
            files_to_include, call_chain, depth=0, max_depth=3
        )
    
    # 收集所有文件信息
    file_list = []
    for fpath in sorted(files_to_include):
        info = index.get(fpath, {})
        file_list.append({
            'path': fpath,
            'role': info.get('role', 'unknown'),
            'class_name': info.get('class_name', ''),
            'package': info.get('package', ''),
        })
    
    http_info = method.get('http_mapping') or {}
    
    return {
        'id': f"{_safe_id(cinfo['class_name'])}_{_safe_id(method['name'])}",
        'entry_file': controller_path,
        'entry_class': cinfo['class_name'],
        'entry_method': method['name'],
        'http_method': http_info.get('http_method', 'N/A'),
        'http_path': http_info.get('path', 'N/A'),
        'files': file_list,
        'mode': 'deep',
    }


def _build_controller_cluster(controller_path: str, cinfo: dict,
                              index: dict, type_to_path: dict) -> dict:
    """为整个 Controller 构建功能簇（overview 模式）。"""
    files_to_include = {controller_path}
    
    # 遍历所有方法，收集依赖
    for method in cinfo['methods']:
        if method.get('body'):
            calls = extract_method_calls(method['body'])
            _resolve_dependencies(
                calls, cinfo['autowired_fields'], index, type_to_path,
                files_to_include, [], depth=0, max_depth=3
            )
    
    file_list = []
    for fpath in sorted(files_to_include):
        info = index.get(fpath, {})
        file_list.append({
            'path': fpath,
            'role': info.get('role', 'unknown'),
            'class_name': info.get('class_name', ''),
            'package': info.get('package', ''),
        })
    
    # 收集所有 HTTP 端点
    endpoints = []
    for m in cinfo['methods']:
        hm = m.get('http_mapping')
        if hm:
            endpoints.append({
                'method': m['name'],
                'http_method': hm['http_method'],
                'path': hm['path'],
                'return_type': m['return_type'],
            })
    
    return {
        'id': f"{_safe_id(cinfo['class_name'])}",
        'entry_file': controller_path,
        'entry_class': cinfo['class_name'],
        'entry_method': None,
        'http_method': 'N/A',
        'http_path': cinfo['class_name'],
        'files': file_list,
        'endpoints': endpoints,
        'mode': 'overview',
    }


def _resolve_dependencies(calls: list, autowired_fields: list,
                          index: dict, type_to_path: dict,
                          files_to_include: set, call_chain: list,
                          depth: int, max_depth: int):
    """递归解析方法调用链中的依赖。"""
    if depth >= max_depth:
        return
    
    # 构建字段名 → 类型名的映射
    field_to_type = {f['field_name']: f['type_name'] for f in autowired_fields}
    
    seen_objects = set()
    for call in calls:
        obj_name = call['target']
        if obj_name in seen_objects:
            continue
        seen_objects.add(obj_name)
        
        type_name = field_to_type.get(obj_name, obj_name)
        
        # 在索引中查找对应的实现文件
        target_path = type_to_path.get(type_name)
        if not target_path:
            # 尝试模糊匹配（处理 Impl 后缀）
            target_path = type_to_path.get(type_name + 'Impl')
        if not target_path and type_name.endswith('Impl'):
            target_path = type_to_path.get(type_name[:-4])
        
        if target_path and target_path not in files_to_include:
            files_to_include.add(target_path)
            target_info = index.get(target_path, {})
            call_chain.append({
                'from_class': 'context',
                'to_class': target_info.get('class_name', ''),
                'to_method': call['method'],
                'to_file': target_path,
            })
            
            # 递归：目标 Service 内部的调用
            target_methods = target_info.get('methods', [])
            target_autowired = target_info.get('autowired_fields', [])
            
            for tm in target_methods:
                if tm.get('body'):
                    inner_calls = extract_method_calls(tm['body'])
                    _resolve_dependencies(
                        inner_calls, target_autowired,
                        index, type_to_path,
                        files_to_include, call_chain,
                        depth + 1, max_depth
                    )


def _safe_id(name: str) -> str:
    """生成安全的 ID。"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).strip('_')


# ── 主入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Java 代码收集与功能簇分组')
    parser.add_argument('--target', required=True, help='Java 项目目录或单个文件')
    parser.add_argument('--mode', choices=['deep', 'overview'], default='overview',
                        help='deep=每个方法一个簇, overview=每个Controller一个簇')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    args = parser.parse_args()
    
    print(f"🔍 扫描 Java 文件: {args.target}")
    java_files = scan_java_files(args.target)
    print(f"   找到 {len(java_files)} 个 Java 文件")
    
    print("📋 构建文件索引...")
    index, type_to_path = build_file_index(java_files)
    
    roles = defaultdict(int)
    for info in index.values():
        roles[info['role']] += 1
    print(f"   文件分布: {dict(roles)}")
    
    print(f"🔗 构建功能簇 (模式: {args.mode})...")
    clusters = build_clusters(index, type_to_path, args.mode)
    print(f"   生成 {len(clusters)} 个功能簇")
    
    result = {
        'target': str(Path(args.target).resolve()),
        'mode': args.mode,
        'total_files': len(java_files),
        'clusters': clusters,
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已输出: {args.output}")
    
    # 打印摘要
    for c in clusters:
        if c['mode'] == 'deep':
            print(f"   📦 {c['id']}: {c['http_method']} {c['http_path']} ({len(c['files'])} 个文件)")
        else:
            print(f"   📦 {c['id']}: {len(c.get('endpoints', []))} 个端点 ({len(c['files'])} 个文件)")


if __name__ == '__main__':
    main()
