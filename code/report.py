#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""policy-tool-extractor · 结果报告生成

读取 output/ 下的统计结果，生成单文件 HTML 报告（内联 SVG 图表，无外部依赖）。

用法：
    python code/report.py
    python code/report.py --out output/report.html

依赖：仅标准库；读取 extractor.py 与 reliability.py 的产物。
"""

from __future__ import annotations

import argparse
import csv
import html
from datetime import date
from pathlib import Path

CAT_ORDER = ["供给型", "环境型", "需求型"]
CAT_COLORS = {"供给型": "#2f6f9f", "环境型": "#4d8b62", "需求型": "#c9722f"}

CSS = """
:root { --ink:#1c1c1c; --muted:#6b6b6b; --line:#e3e3e3; }
* { box-sizing: border-box; }
body { margin:0; padding:44px 20px; color:var(--ink); background:#fff;
       font-family:"Source Han Sans SC","Noto Sans CJK SC","Microsoft YaHei",system-ui,sans-serif;
       line-height:1.7; font-size:15px; }
.wrap { max-width: 880px; margin: 0 auto; }
h1 { font-size:28px; margin:0 0 4px; }
h2 { font-size:18px; margin:40px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--ink); }
h3 { font-size:14px; margin:22px 0 6px; color:var(--muted); }
.sub { color:var(--muted); font-size:13px; margin-bottom:28px; }
.kpis { display:flex; gap:12px; flex-wrap:wrap; margin:20px 0; }
.kpi { flex:1 1 150px; border:1px solid var(--line); border-radius:8px; padding:12px 14px; }
.kpi b { display:block; font-size:24px; }
.kpi span { color:var(--muted); font-size:12px; }
table { width:100%; border-collapse:collapse; margin:10px 0; font-size:13.5px; }
th,td { text-align:left; padding:6px 9px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-size:12.5px; font-weight:600; }
td.num, th.num { text-align:right; font-variant-numeric: tabular-nums; }
.note { background:#f7f7f5; border-left:3px solid #c9c9c2; padding:10px 14px;
        font-size:13px; color:#444; margin:14px 0; }
.foot { margin-top:48px; padding-top:14px; border-top:1px solid var(--line);
        color:var(--muted); font-size:12px; }
code { background:#f2f2ef; padding:1px 5px; border-radius:3px; font-size:12.5px; }
"""


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def svg_bars(data: list[tuple[str, float]], colors: dict[str, str],
             width: int = 780, bar_h: int = 24, gap: int = 9) -> str:
    if not data:
        return '<p class="note">暂无数据</p>'
    label_w, value_w = 150, 70
    height = len(data) * (bar_h + gap) + 8
    max_v = max(v for _, v in data) or 1
    plot_w = width - label_w - value_w
    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
             f'xmlns="http://www.w3.org/2000/svg">']
    for i, (label, value) in enumerate(data):
        y = i * (bar_h + gap) + 4
        w = max(2, plot_w * value / max_v)
        color = colors.get(label, "#8a8a8a")
        parts.append(f'<text x="0" y="{y + bar_h * 0.7:.0f}" font-size="12.5" fill="#333">{esc(label)}</text>')
        parts.append(f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h}" '
                     f'rx="3" fill="{color}" opacity="0.85"/>')
        parts.append(f'<text x="{label_w + w + 8:.0f}" y="{y + bar_h * 0.7:.0f}" '
                     f'font-size="12.5" fill="#555">{value:g}</text>')
    parts.append("</svg>")
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    root = here.parent

    ap = argparse.ArgumentParser(description="生成 HTML 报告")
    ap.add_argument("--out", default=str(Path(root) / "output" / "report.html"))
    ap.add_argument("--title", default="数字政府政策工具分析报告")
    args = ap.parse_args(argv)

    out_dir = Path(here).parent / "output"
    summary = read_csv(out_dir / "tool_summary.csv")
    by_doc = read_csv(out_dir / "tool_counts_by_document.csv")
    reliability = read_csv(out_dir / "reliability.csv")

    if not summary:
        print("缺少 output/tool_summary.csv，请先运行 code/extractor.py")
        return 1

    cat_totals: dict[str, int] = {}
    for r in summary:
        cat = r["一级类目"]
        cat_totals[cat] = cat_totals.get(cat, 0) + int(r["词次合计"])
    grand = sum(cat_totals.values()) or 1

    sub_data = [(r["二级子工具"], int(r["词次合计"])) for r in summary if int(r["词次合计"]) > 0]
    sub_data.sort(key=lambda x: -x[1])
    cat_data = [(c, cat_totals.get(c, 0)) for c in CAT_ORDER if c in cat_totals]

    cat_rows = "".join(
        f"<tr><td>{esc(c)}</td><td class='num'>{n}</td><td class='num'>{n / grand * 100:.1f}%</td></tr>"
        for c, n in cat_data
    )
    sub_rows = "".join(
        f"<tr><td>{esc(r['一级类目'])}</td><td>{esc(r['二级子工具'])}</td>"
        f"<td class='num'>{r['词次合计']}</td><td class='num'>{r['篇次']}</td>"
        f"<td class='num'>{esc(r['覆盖率'])}</td></tr>"
        for r in sorted(summary, key=lambda x: (CAT_ORDER.index(x["一级类目"]), -int(x["词次合计"])))
    )
    doc_rows = "".join(
        f"<tr><td>{esc(r['文件名'][:44])}</td><td class='num'>{r['字符数']}</td>"
        f"<td class='num'>{r['总词次']}</td><td class='num'>{r['命中子工具数']}</td></tr>"
        for r in sorted(by_doc, key=lambda x: -int(x["总词次"]))
    )

    if reliability:
        rel_rows = "".join(
            f"<tr><td>{esc(r['指标'])}</td><td class='num'>{esc(r['取值'])}</td>"
            f"<td class='num'>{esc(r['判定单元数'])}</td><td>{esc(r['说明'])}</td></tr>"
            for r in reliability
        )
        rel_html = (f"<table><thead><tr><th>指标</th><th class='num'>取值</th>"
                    f"<th class='num'>判定单元</th><th>说明</th></tr></thead>"
                    f"<tbody>{rel_rows}</tbody></table>"
                    f"<p class='note'>α ≥ 0.80 通常视为可靠；0.67–0.80 仅可用于探索性结论。"
                    f"分歧明细见 <code>output/disagreements.csv</code>。</p>")
    else:
        rel_html = ('<p class="note">尚未进行双人编码。生成方式：'
                    '<code>python code/extractor.py --binary</code> 得到 0/1 编码矩阵，'
                    '复制一份由第二位编码员独立修订后，运行 '
                    '<code>python code/reliability.py --a ... --b ...</code>。</p>')

    n_docs = len(by_doc)
    n_sub = sum(1 for r in summary if int(r["篇次"]) > 0)
    top = sub_data[0] if sub_data else ("—", 0)

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(args.title)}</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>{esc(args.title)}</h1>
<div class="sub">生成日期 {date.today().isoformat()} · policy-tool-extractor · 关键词词典法（Rothwell &amp; Zegveld 三分法）</div>

<div class="kpis">
  <div class="kpi"><b>{n_docs}</b><span>政策文本</span></div>
  <div class="kpi"><b>{grand}</b><span>关键词总词次</span></div>
  <div class="kpi"><b>{n_sub}</b><span>被使用的子工具</span></div>
  <div class="kpi"><b>{esc(top[0])}</b><span>最高频子工具（{top[1]} 次）</span></div>
</div>

<h2>一、一级类目分布</h2>
{svg_bars(cat_data, CAT_COLORS)}
<table><thead><tr><th>类目</th><th class="num">词次</th><th class="num">占比</th></tr></thead>
<tbody>{cat_rows}</tbody></table>

<h2>二、二级子工具（词次）</h2>
{svg_bars(sub_data[:14], {}, width=780, bar_h=20, gap=7)}
<table><thead><tr><th>类目</th><th>子工具</th><th class="num">词次</th><th class="num">篇次</th><th class="num">覆盖率</th></tr></thead>
<tbody>{sub_rows}</tbody></table>

<h2>三、分省明细</h2>
<table><thead><tr><th>文件</th><th class="num">字符数</th><th class="num">总词次</th><th class="num">命中子工具</th></tr></thead>
<tbody>{doc_rows}</tbody></table>

<h2>四、编码信度</h2>
{rel_html}

<h2>五、方法说明（可直接改写进论文）</h2>
<p>本研究以 Rothwell &amp; Zegveld（1985）的政策工具三分法为框架，将政策文本中的工具表述
划分为供给型、环境型、需求型三类，并细分为 14 个二级子工具。采用关键词词典法进行机器初筛，
每条命中均保留所在文本以便人工复核。编码手册见 <code>docs/coding_sheet.md</code>，
词典实现见 <code>code/extractor.py</code>。</p>
<p>统计报告两种口径：<strong>词次</strong>（关键词在全文出现的总次数，反映表述强度）与
<strong>篇次</strong>（出现该子工具的文档数，反映使用广度）。两者不可混用，文中已分别标注。</p>
<p><strong>可复现性声明</strong>：本报告由 <code>code/extractor.py</code> 与
<code>code/report.py</code> 自动生成，输入为 <code>data/raw/</code> 下的政策文本，
执行相同命令可逐字节复现。</p>

<div class="foot">
policy-tool-extractor · 关键词词典法 · 政策文本版权归原发布机关，仅用于学术研究
</div>
</div></body></html>"""

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"报告已生成：{out}（{len(doc):,} 字符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
