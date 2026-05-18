#!/usr/bin/env python3
"""
html_assembler.py — 将最终数据模型组装为自包含 HTML 文档

用法:
  python3 html_assembler.py --model final_model.json --output 订单模块_业务文档.html

输出: 单个 HTML 文件，含 Mermaid 时序图/流程图，浏览器打开即看
"""

import argparse, json, sys
from datetime import datetime
from pathlib import Path


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg: #f8f9fa;
    --sidebar-bg: #1a1a2e;
    --sidebar-text: #e0e0e0;
    --card-bg: #ffffff;
    --text: #2d3436;
    --text-secondary: #636e72;
    --border: #dfe6e9;
    --accent: #0984e3;
    --accent-light: #d4e6f9;
    --tag-bg: #e8f4fd;
    --tag-text: #0984e3;
    --method-get: #00b894;
    --method-post: #0984e3;
    --method-put: #e17055;
    --method-delete: #d63031;
    --code-bg: #f1f2f6;
    --shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}

  [data-theme="dark"] {{
    --bg: #1a1a2e;
    --sidebar-bg: #111122;
    --card-bg: #252540;
    --text: #e0e0e0;
    --text-secondary: #a0a0b0;
    --border: #3a3a55;
    --accent: #74b9ff;
    --accent-light: #1e3a5f;
    --tag-bg: #1e3a5f;
    --tag-text: #74b9ff;
    --code-bg: #2d2d44;
    --shadow: 0 1px 3px rgba(0,0,0,0.3);
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    min-height: 100vh;
  }}

  /* 侧边栏 */
  .sidebar {{
    width: 280px;
    min-width: 280px;
    background: var(--sidebar-bg);
    color: var(--sidebar-text);
    padding: 20px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
    z-index: 10;
  }}

  .sidebar h1 {{
    font-size: 18px;
    margin-bottom: 8px;
    color: #fff;
  }}

  .sidebar .meta {{
    font-size: 12px;
    color: #888;
    margin-bottom: 20px;
  }}

  .sidebar .search-box {{
    width: 100%;
    padding: 8px 12px;
    border: none;
    border-radius: 6px;
    background: rgba(255,255,255,0.1);
    color: #fff;
    font-size: 13px;
    margin-bottom: 16px;
    outline: none;
  }}

  .sidebar .search-box::placeholder {{ color: #888; }}

  .sidebar nav a {{
    display: block;
    padding: 6px 8px;
    color: #b0b0c0;
    text-decoration: none;
    font-size: 13px;
    border-radius: 4px;
    margin-bottom: 2px;
    transition: background 0.15s;
  }}

  .sidebar nav a:hover, .sidebar nav a.active {{
    background: rgba(255,255,255,0.1);
    color: #fff;
  }}

  /* 主内容 */
  .main {{
    flex: 1;
    padding: 30px 40px;
    max-width: 1100px;
  }}

  .api-card {{
    background: var(--card-bg);
    border-radius: 8px;
    box-shadow: var(--shadow);
    padding: 28px 32px;
    margin-bottom: 24px;
    border: 1px solid var(--border);
  }}

  .api-card.failed {{
    border-left: 3px solid #e17055;
    opacity: 0.8;
  }}

  .api-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }}

  .http-tag {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
    color: #fff;
    letter-spacing: 1px;
  }}

  .http-tag.GET {{ background: var(--method-get); }}
  .http-tag.POST {{ background: var(--method-post); }}
  .http-tag.PUT {{ background: var(--method-put); }}
  .http-tag.DELETE {{ background: var(--method-delete); }}
  .http-tag.PATCH {{ background: #a29bfe; }}

  .api-path {{
    font-family: "SF Mono", "Fira Code", monospace;
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
  }}

  h2 {{ font-size: 20px; margin: 24px 0 12px; color: var(--text); }}
  h3 {{ font-size: 16px; margin: 20px 0 8px; color: var(--text); }}

  p, li {{ line-height: 1.7; color: var(--text-secondary); }}
  ul, ol {{ padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}

  .summary-block {{
    background: var(--accent-light);
    border-left: 3px solid var(--accent);
    padding: 12px 16px;
    border-radius: 4px;
    margin: 16px 0;
    font-size: 14px;
  }}

  .mermaid-block {{
    background: var(--code-bg);
    border-radius: 6px;
    padding: 16px;
    margin: 16px 0;
    overflow-x: auto;
  }}

  .mermaid-block pre {{
    margin: 0;
    font-size: 13px;
    white-space: pre;
    font-family: "SF Mono", "Fira Code", monospace;
  }}

  .rule-list {{
    list-style: none;
    padding: 0;
  }}

  .rule-list li {{
    padding: 6px 12px;
    margin: 4px 0;
    background: var(--code-bg);
    border-radius: 4px;
    font-size: 13px;
  }}

  .rule-list li::before {{
    content: "⚡ ";
    color: var(--accent);
  }}

  .verify-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }}

  .verify-badge.pass {{ background: #d4edda; color: #155724; }}
  .verify-badge.warn {{ background: #fff3cd; color: #856404; }}
  .verify-badge.none {{ background: #f1f2f6; color: #636e72; }}

  .toolbar {{
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
  }}

  .toolbar button {{
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--card-bg);
    color: var(--text);
    cursor: pointer;
    font-size: 13px;
  }}

  .toolbar button:hover {{ background: var(--accent-light); }}

  @media print {{
    .sidebar {{ display: none; }}
    .main {{ padding: 0; }}
    .api-card {{ box-shadow: none; border: 1px solid #ddd; break-inside: avoid; }}
  }}

  @media (max-width: 768px) {{
    body {{ flex-direction: column; }}
    .sidebar {{ width: 100%; min-width: 100%; height: auto; position: static; }}
    .main {{ padding: 16px; }}
  }}
</style>
</head>
<body>

<aside class="sidebar">
  <h1>{title}</h1>
  <div class="meta">
    {total_apis} 个接口 · {generated_at}
  </div>
  <input type="text" class="search-box" placeholder="🔍 搜索接口..." oninput="filterAPIs(this.value)">
  <nav>
    {nav_links}
  </nav>
</aside>

<main class="main">
  <div class="toolbar">
    <button onclick="toggleTheme()">{theme_toggle}</button>
    <button onclick="window.print()">🖨️ 打印</button>
  </div>
  {api_cards}
</main>

<script>
  // 暗色模式切换
  function toggleTheme() {{
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    if (current === 'dark') {{
      html.removeAttribute('data-theme');
      localStorage.setItem('theme', 'light');
    }} else {{
      html.setAttribute('data-theme', 'dark');
      localStorage.setItem('theme', 'dark');
    }}
  }}

  // 读取保存的主题
  (function() {{
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {{
      document.documentElement.setAttribute('data-theme', 'dark');
    }}
  }})();

  // 搜索过滤
  function filterAPIs(query) {{
    const cards = document.querySelectorAll('.api-card');
    const links = document.querySelectorAll('.sidebar nav a');
    const q = query.toLowerCase();
    
    cards.forEach((card, i) => {{
      const text = card.textContent.toLowerCase();
      if (!q || text.includes(q)) {{
        card.style.display = '';
        if (links[i]) links[i].style.display = '';
      }} else {{
        card.style.display = 'none';
        if (links[i]) links[i].style.display = 'none';
      }}
    }});
  }}

  // Mermaid 渲染
  document.addEventListener('DOMContentLoaded', function() {{
    if (typeof mermaid !== 'undefined') {{
      mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
    }} else {{
      // Mermaid.js 加载失败的提示
      const blocks = document.querySelectorAll('.mermaid-block');
      blocks.forEach(block => {{
        block.innerHTML = '<p style="color:#e17055">⚠️ Mermaid.js 未加载（CDN 可能不可访问）。</p>'
          + '<p style="font-size:12px">请将 mermaid.min.js 放到本文件同目录，或检查网络连接。</p>'
          + '<details><summary>查看原始 Mermaid 代码</summary>'
          + block.innerHTML + '</details>';
      }});
    }}
  }});
</script>

<!-- Mermaid.js CDN -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>

</body>
</html>'''


NAV_ITEM_TEMPLATE = '''<a href="#{cluster_id}" data-search="{search_text}">{label}</a>'''


def build_nav_links(apis: list) -> str:
    """构建侧边栏导航。"""
    links = []
    for api in apis:
        cid = api['cluster_id']
        if api['mode'] == 'deep':
            label = f"{api['http_method']} {api['http_path']}"
        else:
            label = f"📦 {api['entry_class']}"
        
        search_text = f"{api['http_method']} {api['http_path']} {api['entry_class']}"
        links.append(NAV_ITEM_TEMPLATE.format(
            cluster_id=cid,
            search_text=search_text,
            label=label,
        ))
    return '\n    '.join(links)


def build_api_card(api: dict) -> str:
    """构建单个 API 的 HTML 卡片。"""
    cid = api['cluster_id']
    
    # 失败的处理
    if api['status'] == 'failed':
        return f'''
<div class="api-card failed" id="{cid}">
  <div class="api-header">
    <span class="http-tag">ERR</span>
    <span class="api-path">{api.get('http_path', cid)}</span>
    <span class="failed-badge">⚠️ 分析失败</span>
  </div>
  <p style="color:#e17055">{api.get('error', '未知错误')}</p>
</div>'''
    
    # 成功的卡片
    http_method = api.get('http_method', 'N/A')
    http_path = api.get('http_path', '')
    
    parts = [f'''
<div class="api-card" id="{cid}">
  <div class="api-header">
    <span class="http-tag {http_method}">{http_method}</span>
    <span class="api-path">{http_path}</span>
  </div>''']
    
    # 业务概述
    if api.get('summary'):
        parts.append(f'''
  <div class="summary-block">{api['summary']}</div>''')
    
    # 时序图
    if api.get('sequence_diagram'):
        parts.append(f'''
  <h3>📊 调用时序图</h3>
  <div class="mermaid-block">
    <pre class="mermaid">
{api['sequence_diagram']}
    </pre>
  </div>''')
    
    # 流程图
    if api.get('flowchart_diagram'):
        parts.append(f'''
  <h3>🔄 业务流程</h3>
  <div class="mermaid-block">
    <pre class="mermaid">
{api['flowchart_diagram']}
    </pre>
  </div>''')
    
    # 分步流程
    if api.get('flow'):
        flow_items = '\n'.join(f'    <li>{escape_html(s)}</li>' for s in api['flow'])
        parts.append(f'''
  <h3>📋 分步流程</h3>
  <ol>
{flow_items}
  </ol>''')
    
    # 业务规则
    if api.get('rules'):
        rules = '\n'.join(f'    <li>{escape_html(r)}</li>' for r in api['rules'])
        parts.append(f'''
  <h3>⚡ 关键业务规则</h3>
  <ul class="rule-list">
{rules}
  </ul>''')
    
    # 数据模型
    if api.get('data_models'):
        models = '\n'.join(f'    <li>{escape_html(m)}</li>' for m in api['data_models'])
        parts.append(f'''
  <h3>📦 数据模型</h3>
  <ul>
{models}
  </ul>''')
    
    # 异常处理
    if api.get('exceptions'):
        parts.append(f'''
  <h3>⚠️ 异常与边界情况</h3>
  <p>{escape_html(api['exceptions'])}</p>''')
    
    # 校验状态 & 修正
    if api.get('verified') is True:
        if api.get('verification_passed'):
            parts.append(f'''
  <div style="background:#d4edda;border-left:3px solid #28a745;padding:8px 12px;border-radius:4px;font-size:13px;margin-top:12px">
    ✅ 二次校验通过 — 分析结果与代码一致
  </div>''')
        elif api.get('corrections'):
            corr_items = []
            for c in api['corrections']:
                corr_items.append(f'''
      <div style="margin-bottom:8px;padding:8px;background:#fff3cd;border-radius:4px">
        <span style="color:#856404;font-weight:600">[{escape_html(c.get('type', ''))}]</span><br>
        <span style="text-decoration:line-through;color:#999">原: {escape_html(c.get('original', ''))}</span><br>
        <span style="color:#28a745">→ 修正: {escape_html(c.get('corrected', ''))}</span><br>
        <small style="color:#666">原因: {escape_html(c.get('reason', ''))}</small>
      </div>''')
            parts.append(f'''
  <details style="margin-top:12px">
    <summary style="cursor:pointer;color:#856404;font-weight:600">🔧 二次校验发现 {len(api['corrections'])} 处修正</summary>
    {''.join(corr_items)}
  </details>''')
    
    parts.append('</div>')
    return '\n'.join(parts)


def escape_html(text: str) -> str:
    """HTML 转义。"""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def main():
    parser = argparse.ArgumentParser(description='组装 HTML 业务文档')
    parser.add_argument('--model', required=True, help='final_model.json 路径')
    parser.add_argument('--output', required=True, help='输出 HTML 文件路径')
    args = parser.parse_args()
    
    with open(args.model, 'r', encoding='utf-8') as f:
        model = json.load(f)
    
    apis = model['apis']
    
    # 生成 HTML
    title = Path(args.output).stem.replace('_', ' ')
    nav_links = build_nav_links(apis)
    api_cards = '\n'.join(build_api_card(api) for api in apis)
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    html = HTML_TEMPLATE.format(
        title=f"{title} · 业务逻辑文档",
        total_apis=f"{model['success_count']}/{len(apis)}",
        generated_at=generated_at,
        nav_links=nav_links,
        api_cards=api_cards,
        theme_toggle='🌙 暗色模式',
    )
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 文档已生成: {args.output}")
    print(f"   共 {len(apis)} 个接口卡片，{model['success_count']} 个成功分析")


if __name__ == '__main__':
    main()
