#!/usr/bin/env python3
"""
html_assembler.py — 将最终数据模型组装为自包含 HTML 文档

支持多受众：
  --audience technical (默认): 面向技术人员
  --audience newcomer: 面向产品经理和运维菜鸟（含术语解释、新手引导、运维操作区）

用法:
  python3 html_assembler.py --model final_model.json --output 业务文档.html
  python3 html_assembler.py --model final_model.json --output 业务文档.html --audience newcomer
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# 模板 1：技术人员版（原有风格）
# ============================================================
TECHNICAL_HTML_TEMPLATE = '''<!DOCTYPE html>
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

  (function() {{
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {{
      document.documentElement.setAttribute('data-theme', 'dark');
    }}
  })();

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

  document.addEventListener('DOMContentLoaded', function() {{
    if (typeof mermaid !== 'undefined') {{
      mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
    }} else {{
      const blocks = document.querySelectorAll('.mermaid-block');
      blocks.forEach(block => {{
        block.innerHTML = '<p style="color:#e17055">⚠️ Mermaid.js 未加载。</p>'
          + '<details><summary>查看原始 Mermaid 代码</summary>'
          + block.innerHTML + '</details>';
      }});
    }}
  }});
</script>

<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>

</body>
</html>'''


# ============================================================
# 模板 2：新人版（产品经理/运维菜鸟）
# ============================================================
NEWCOMER_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — 新人引导版</title>
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
    --tip-bg: #fff9e6;
    --tip-border: #ffd93d;
    --ops-bg: #e8f5e9;
    --ops-border: #4caf50;
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
    --tip-bg: #2d2d00;
    --tip-border: #ffd93d;
    --ops-bg: #1b3d1b;
    --ops-border: #4caf50;
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
    width: 300px;
    min-width: 300px;
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
    max-width: 1200px;
  }}

  /* 新手指引区 */
  .intro-banner {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    padding: 24px 32px;
    color: #fff;
    margin-bottom: 28px;
  }}

  .intro-banner h2 {{
    font-size: 20px;
    margin-bottom: 12px;
    color: #fff;
  }}

  .intro-banner p {{
    font-size: 14px;
    line-height: 1.8;
    color: rgba(255,255,255,0.9);
    margin-bottom: 16px;
  }}

  .intro-glossary {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}

  .glossary-item {{
    background: rgba(255,255,255,0.2);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 12px;
    cursor: help;
    position: relative;
  }}

  .glossary-item:hover::after {{
    content: attr(data-tip);
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    color: #fff;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    white-space: nowrap;
    z-index: 100;
    max-width: 250px;
    white-space: normal;
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

  /* 面包屑 */
  .breadcrumb {{
    font-size: 12px;
    color: #888;
    margin-bottom: 12px;
  }}

  .breadcrumb span {{
    margin-right: 8px;
  }}

  .breadcrumb .current {{
    color: var(--accent);
    font-weight: 600;
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
  li {{ margin-bottom: 6px; }}

  .summary-block {{
    background: var(--accent-light);
    border-left: 3px solid var(--accent);
    padding: 12px 16px;
    border-radius: 4px;
    margin: 16px 0;
    font-size: 14px;
  }}

  .summary-block strong {{
    color: var(--accent);
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
    padding: 8px 12px;
    margin: 4px 0;
    background: var(--code-bg);
    border-radius: 4px;
    font-size: 13px;
  }}

  .rule-list li::before {{
    content: "⚡ ";
    color: var(--accent);
  }}

  /* 新人提示框 */
  .tip-box {{
    background: var(--tip-bg);
    border-left: 3px solid var(--tip-border);
    padding: 12px 16px;
    border-radius: 4px;
    margin: 16px 0;
    font-size: 13px;
  }}

  .tip-box strong {{
    color: #856404;
  }}

  /* 运维操作区 */
  .ops-box {{
    background: var(--ops-bg);
    border-left: 3px solid var(--ops-border);
    padding: 12px 16px;
    border-radius: 4px;
    margin: 16px 0;
    font-size: 13px;
  }}

  .ops-box h4 {{
    font-size: 13px;
    color: #2e7d32;
    margin-bottom: 8px;
  }}

  .ops-box code {{
    background: rgba(0,0,0,0.1);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 12px;
  }}

  /* 步骤进度 */
  .step-progress {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 12px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }}

  .step-num {{
    background: var(--accent);
    color: #fff;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
  }}

  /* 数据模型表格 */
  .data-model-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13px;
  }}

  .data-model-table th {{
    background: var(--code-bg);
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    border: 1px solid var(--border);
  }}

  .data-model-table td {{
    padding: 8px 12px;
    border: 1px solid var(--border);
  }}

  .data-model-table tr:nth-child(even) {{
    background: var(--code-bg);
  }}

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
  <h1>📚 {title}</h1>
  <div class="meta">
    {total_apis} 个接口 · {generated_at}
  </div>
  <div style="font-size:11px;color:#888;margin-bottom:12px;">
    👶 新人引导版 · 产品经理/运维适用
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

  <!-- 新手指引区 -->
  <div class="intro-banner">
    <h2>👋 欢迎阅读业务文档</h2>
    <p>这是一份面向新人的业务文档。如果你不理解某些术语，请查看下方的术语表，或将鼠标悬停在 <span style="background:rgba(255,255,255,0.2);padding:2px 8px;border-radius:4px;">紫色高亮</span> 的术语上。</p>
    <div class="intro-glossary">
      <span class="glossary-item" data-tip="API = Application Programming Interface，应用程序编程接口。可以理解为系统与系统之间的对话窗口。">API 是什么？</span>
      <span class="glossary-item" data-tip="HTTP方法：GET=获取数据，POST=提交数据，PUT=更新数据，DELETE=删除数据。">HTTP 方法</span>
      <span class="glossary-item" data-tip="调用链 = 从发起请求到返回结果的完整路径。就像点外卖：下单→商家接单→制作→骑手取餐→配送→送达。">什么是调用链？</span>
      <span class="glossary-item" data-tip="接口 = API的另一个叫法。就像餐厅的菜单，告诉你能点什么菜。">接口 vs API</span>
      <span class="glossary-item" data-tip="返回码 = 系统告诉你请求结果的方式。200=成功，400=请求错误，500=服务器错误。">返回码</span>
      <span class="glossary-item" data-tip="参数 = 调用接口时需要提供的信息，就像打电话需要拨号码。">参数</span>
    </div>
  </div>

  {api_cards}
</main>

<script>
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

  (function() {{
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {{
      document.documentElement.setAttribute('data-theme', 'dark');
    }}
  })();

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

  document.addEventListener('DOMContentLoaded', function() {{
    if (typeof mermaid !== 'undefined') {{
      mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
    }} else {{
      const blocks = document.querySelectorAll('.mermaid-block');
      blocks.forEach(block => {{
        block.innerHTML = '<p style="color:#e17055">⚠️ Mermaid.js 未加载（CDN 可能不可访问）。请检查网络连接。</p>'
          + '<details><summary>查看原始 Mermaid 代码</summary>'
          + block.innerHTML + '</details>';
      }});
    }}
  }});
</script>

<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>

</body>
</html>'''


NAV_ITEM_TEMPLATE = '<a href="#{cluster_id}" data-search="{search_text}">{label}</a>'


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


def build_api_card_technical(api: dict) -> str:
    """构建技术人员版的 API 卡片。"""
    cid = api['cluster_id']

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

    http_method = api.get('http_method', 'N/A')
    http_path = api.get('http_path', '')

    parts = [f'''
<div class="api-card" id="{cid}">
  <div class="api-header">
    <span class="http-tag {http_method}">{http_method}</span>
    <span class="api-path">{http_path}</span>
  </div>''']

    if api.get('summary'):
        parts.append(f'''
  <div class="summary-block">{api['summary']}</div>''')

    if api.get('sequence_diagram'):
        parts.append(f'''
  <h3>📊 调用时序图</h3>
  <div class="mermaid-block">
    <pre class="mermaid">
{api['sequence_diagram']}
    </pre>
  </div>''')

    if api.get('flowchart_diagram'):
        parts.append(f'''
  <h3>🔄 业务流程</h3>
  <div class="mermaid-block">
    <pre class="mermaid">
{api['flowchart_diagram']}
    </pre>
  </div>''')

    if api.get('flow'):
        flow_items = '\n'.join(f'    <li>{escape_html(s)}</li>' for s in api['flow'])
        parts.append(f'''
  <h3>📋 分步流程</h3>
  <ol>
{flow_items}
  </ol>''')

    if api.get('rules'):
        rules = '\n'.join(f'    <li>{escape_html(r)}</li>' for r in api['rules'])
        parts.append(f'''
  <h3>⚡ 关键业务规则</h3>
  <ul class="rule-list">
{rules}
  </ul>''')

    if api.get('data_models'):
        models = '\n'.join(f'    <li>{escape_html(m)}</li>' for m in api['data_models'])
        parts.append(f'''
  <h3>📦 数据模型</h3>
  <ul>
{models}
  </ul>''')

    if api.get('exceptions'):
        parts.append(f'''
  <h3>⚠️ 异常与边界情况</h3>
  <p>{escape_html(api['exceptions'])}</p>''')

    parts.append('</div>')
    return '\n'.join(parts)


def build_api_card_newcomer(api: dict) -> str:
    """构建新人版的 API 卡片（含面包屑、步骤进度、运维操作区）。"""
    cid = api['cluster_id']

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

    http_method = api.get('http_method', 'N/A')
    http_path = api.get('http_path', '')
    entry_class = api.get('entry_class', 'Unknown')

    parts = [f'''
<div class="api-card" id="{cid}">
  <div class="breadcrumb">
    <span>📄 文档</span> ›
    <span>{entry_class}</span> ›
    <span class="current">{http_path}</span>
  </div>
  <div class="api-header">
    <span class="http-tag {http_method}">{http_method}</span>
    <span class="api-path">{http_path}</span>
  </div>''']

    # 业务概述（新人版加粗核心概念）
    if api.get('summary'):
        parts.append(f'''
  <div class="summary-block"><strong>这段话在说：</strong>{api['summary']}</div>''')

    # 分步流程（带进度指示）
    if api.get('flow'):
        flow_items = []
        for i, step in enumerate(api['flow'], 1):
            flow_items.append(f'    <li><span class="step-num">{i}</span> {escape_html(step)}</li>')
        parts.append(f'''
  <h3>📋 业务流程（共 {len(api['flow'])} 步）</h3>
  <div class="step-progress">跟着这个步骤走，就能完成整个操作</div>
  <ol>
{'\n'.join(flow_items)}
  </ol>''')

    # 业务规则
    if api.get('rules'):
        rules = '\n'.join(f'    <li>{escape_html(r)}</li>' for r in api['rules'])
        parts.append(f'''
  <h3>⚡ 关键业务规则</h3>
  <div class="tip-box"><strong>💡 记住：</strong>这些规则决定了你能不能做某件事，以及做的时候要注意什么</div>
  <ul class="rule-list">
{rules}
  </ul>''')

    # 数据模型（表格形式）
    if api.get('data_models'):
        model_rows = []
        for m in api['data_models']:
            model_rows.append(f'    <tr><td>{escape_html(m)}</td></tr>')
        parts.append(f'''
  <h3>📦 数据模型</h3>
  <div class="tip-box"><strong>📝 字段说明：</strong>以下是你需要了解的数据结构</div>
  <table class="data-model-table">
    <tr><th>字段</th></tr>
{'\n'.join(model_rows)}
  </table>''')

    # 调用时序图
    if api.get('sequence_diagram'):
        parts.append(f'''
  <h3>📊 调用时序图</h3>
  <div class="mermaid-block">
    <pre class="mermaid">
{api['sequence_diagram']}
    </pre>
  </div>''')

    # 异常与边界情况
    if api.get('exceptions'):
        parts.append(f'''
  <h3>⚠️ 异常与边界情况</h3>
  <div class="tip-box"><strong>⚠️ 注意：</strong>如果遇到以下情况，按建议处理</div>
  <p>{escape_html(api['exceptions'])}</p>''')

    # 运维操作区
    ops_tips = build_ops_tips(api)
    if ops_tips:
        parts.append(f'''
  <div class="ops-box">
    <h4>🔧 运维关注点</h4>
    {ops_tips}
  </div>''')

    parts.append('</div>')
    return '\n'.join(parts)


def build_ops_tips(api: dict) -> str:
    """为新人版构建运维关注点提示。"""
    tips = []
    http_method = api.get('http_method', '')
    http_path = api.get('http_path', '')

    # GET 接口通常可以重试
    if http_method == 'GET':
        tips.append(f'• <code>curl -X GET {http_path}</code> — 健康检查时可以调用此接口')
        tips.append('• 这个接口是查询操作，幂等的，可以放心重试')

    # POST 接口需要小心
    if http_method == 'POST':
        tips.append(f'• <code>curl -X POST {http_path}</code> — 调用时注意参数格式')
        tips.append('• 这是提交类操作，重复提交可能产生重复数据，请确认业务幂等性')

    # PUT/DELETE 要谨慎
    if http_method in ('PUT', 'DELETE'):
        tips.append(f'• <code>curl -X {http_method} {http_path}</code> — 修改/删除操作，调用前请确认')
        tips.append('• 这类操作不可逆，务必做好数据备份')

    # 有异常处理的话，给出排查建议
    if api.get('exceptions'):
        tips.append('• 异常处理参考上方"⚠️ 异常与边界情况"章节')

    if not tips:
        return ''

    return '<br>'.join(tips)


def escape_html(text: str) -> str:
    """HTML 转义。"""
    if not text:
        return ''
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def main():
    parser = argparse.ArgumentParser(description='组装 HTML 业务文档')
    parser.add_argument('--model', required=True, help='final_model.json 路径')
    parser.add_argument('--output', required=True, help='输出 HTML 文件路径')
    parser.add_argument('--audience', default='technical', choices=['technical', 'newcomer'],
                        help='受众类型: technical (默认) 或 newcomer (产品经理/运维)')
    args = parser.parse_args()

    with open(args.model, 'r', encoding='utf-8') as f:
        model = json.load(f)

    apis = model['apis']

    # 选择模板和卡片构建器
    if args.audience == 'newcomer':
        template = NEWCOMER_HTML_TEMPLATE
        card_builder = build_api_card_newcomer
        title_suffix = '新人引导版'
    else:
        template = TECHNICAL_HTML_TEMPLATE
        card_builder = build_api_card_technical
        title_suffix = '业务逻辑文档'

    # 生成 HTML
    title = Path(args.output).stem.replace('_', ' ')
    nav_links = build_nav_links(apis)
    api_cards = '\n'.join(card_builder(api) for api in apis)
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M')

    html = template.format(
        title=f"{title}",
        total_apis=f"{model['success_count']}/{len(apis)}",
        generated_at=generated_at,
        nav_links=nav_links,
        api_cards=api_cards,
        theme_toggle='🌙 暗色模式',
    )

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)

    audience_label = '新人引导版' if args.audience == 'newcomer' else '技术版'
    print(f"✅ {audience_label} HTML 文档已生成: {args.output}")
    print(f"   共 {len(apis)} 个接口卡片，{model['success_count']} 个成功分析")


if __name__ == '__main__':
    main()