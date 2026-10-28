#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""policy-tool-extractor · 政策工具关键词提取器

批量读取 data/raw/ 下的政策文本（.txt），按 Rothwell & Zegveld 三分法
（供给型 / 环境型 / 需求型）及二级子工具做关键词匹配，统计频次并输出 CSV。

用法：
    python code/extractor.py
    python code/extractor.py --raw data/raw --out output

输出：
    output/tool_counts_by_document.csv   每篇文本 × 每个子工具的命中次数
    output/tool_summary.csv              子工具汇总（词次 / 篇次 / 覆盖率）

仅依赖标准库。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 关键词词典
# 结构：一级类目 -> 二级子工具 -> 关键词列表
# 说明：面向「数字政府」场景做了扩充（政务云、一网通办、数据共享等）
KEYWORDS: dict[str, dict[str, list[str]]] = {
    "供给型": {
        "资金投入": ["财政拨款", "专项资金", "资金保障", "经费保障", "财政投入",
                     "资金支持", "预算安排", "以奖代补", "投入机制", "资金投入"],
        "人才培养": ["人才培养", "人才引进", "培训", "队伍建设", "数字素养",
                     "专业人才", "人才梯队", "继续教育", "干部培训"],
        "技术支持": ["技术研发", "关键技术", "科技攻关", "创新平台", "成果转化",
                     "技术标准", "人工智能", "大模型", "区块链", "算法", "算力"],
        "公共服务": ["政务服务平台", "一网通办", "便民服务", "服务网络",
                     "一体化平台", "政务云", "电子证照", "移动端", "掌上办",
                     "公共服务", "政务服务"],
        "信息支持": ["信息公开", "数据共享", "数据开放", "信息发布", "统计监测",
                     "宣传引导", "数据目录", "信息共享", "数据汇聚"],
    },
    "环境型": {
        "目标规划": ["规划", "纲要", "行动方案", "实施意见", "指导意见", "目标",
                     "指标", "时间表", "路线图", "五年", "实施方案"],
        "法规管制": ["条例", "法规", "规章", "管理办法", "监督管理", "执法",
                     "处罚", "准入", "退出机制", "安全评估", "备案", "责任制",
                     "标准规范", "合规", "监管"],
        "金融支持": ["信贷", "融资", "保险", "担保", "产业基金", "金融服务",
                     "投融资", "债券"],
        "税收优惠": ["税收优惠", "减免税", "税前扣除", "税率", "免征", "增值税",
                     "所得税", "税收"],
        "策略性措施": ["试点", "示范", "考核", "评价", "督导", "组织领导",
                       "统筹协调", "部门协同", "激励机制", "联席会议", "工作机制",
                       "专班", "清单"],
    },
    "需求型": {
        "政府采购": ["政府采购", "政府购买服务", "集中采购", "首台套", "招标",
                     "采购"],
        "价格补贴": ["价格补贴", "消费补贴", "补助标准", "收费减免", "降价",
                     "优惠", "补贴"],
        "贸易管制": ["进出口", "关税", "市场准入", "负面清单", "许可管理"],
        "海外交流": ["国际合作", "跨境", "国际交流", "走出去", "海外",
                     "国际规则"],
    },
}

WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """去除空白，避免排版断行导致漏检。"""
    return WS.sub("", text)


def count_hits(text: str, keywords: list[str]) -> int:
    """统计一组关键词在文本中的总出现次数。"""
    return sum(text.count(kw) for kw in keywords)


def analyze(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    text = normalize(raw)
    row = {"文件名": path.name, "字符数": len(text)}
    for category, subs in KEYWORDS.items():
        for sub, kws in subs.items():
            row[sub] = count_hits(text, kws)
    row["总词次"] = sum(v for k, v in row.items() if isinstance(v, int) and k not in ("字符数",))
    row["命中子工具数"] = sum(
        1 for category, subs in KEYWORDS.items() for sub in subs if row.get(sub, 0) > 0
    )
    return row


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    root = here.parent

    ap = argparse.ArgumentParser(description="政策工具关键词提取器")
    ap.add_argument("--raw", default=str(root / "data" / "raw"), help="政策文本目录")
    ap.add_argument("--out", default=str(root / "output"), help="输出目录")
    ap.add_argument("--binary", action="store_true",
                    help="额外输出 0/1 编码矩阵（可作为人工编码表或信度检验输入）")
    args = ap.parse_args(argv)

    raw_dir = Path(args.raw)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in raw_dir.glob("*.txt") if p.is_file())
    if not files:
        print(f"未在 {raw_dir} 找到 .txt 文件", file=sys.stderr)
        return 1

    rows = [analyze(p) for p in files]
    subs = [sub for category, d in KEYWORDS.items() for sub in d]
    doc_fields = ["文件名", "字符数"] + subs + ["总词次", "命中子工具数"]

    by_doc = out_dir / "tool_counts_by_document.csv"
    with by_doc.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=doc_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, 0) for k in doc_fields})

    summary_rows = []
    for category, d in KEYWORDS.items():
        for sub, kws in d.items():
            total = sum(r[sub] for r in rows)
            docs = sum(1 for r in rows if r[sub] > 0)
            summary_rows.append({
                "一级类目": category,
                "二级子工具": sub,
                "词次合计": total,
                "篇次": docs,
                "覆盖率": f"{docs / len(rows) * 100:.1f}%",
                "关键词数": len(kws),
            })

    by_sum = out_dir / "tool_summary.csv"
    with by_sum.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["一级类目", "二级子工具", "词次合计", "篇次", "覆盖率", "关键词数"])
        w.writeheader()
        w.writerows(summary_rows)

    cat_totals: dict[str, int] = {}
    for r in summary_rows:
        cat_totals[r["一级类目"]] = cat_totals.get(r["一级类目"], 0) + r["词次合计"]

    if args.binary:
        matrix_path = out_dir / "coding_matrix.csv"
        with matrix_path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=["文件名"] + subs)
            w.writeheader()
            for r in rows:
                w.writerow({"文件名": r["文件名"], **{s: 1 if r[s] > 0 else 0 for s in subs}})
        print(f"  {matrix_path.name}（0/1 编码矩阵，可直接作为人工编码表）")

    print(f"处理文本 {len(rows)} 篇，输出目录 {out_dir}")
    print(f"  {by_doc.name}")
    print(f"  {by_sum.name}")
    print("\n一级类目词次合计：")
    grand = sum(cat_totals.values()) or 1
    for cat, n in sorted(cat_totals.items(), key=lambda kv: -kv[1]):
        print(f"  {cat}: {n} ({n / grand * 100:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
