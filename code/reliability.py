#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""policy-tool-extractor · 编码信度检验

输入两份「文档 × 子工具」的 0/1 编码矩阵（由 extractor.py --binary 生成，
或由两名编码员各自填写），计算：

  - 简单一致率（percent agreement）
  - Krippendorff's α（名义尺度，支持缺失值）
  - Cohen's κ（仅两名编码员）
  - 分歧单元清单（供逐条复核）

用法：
    python code/extractor.py --binary --out output
    # 得到 output/coding_matrix.csv，复制一份作为第二位编码员的表，人工修订
    python code/reliability.py --a output/coding_matrix.csv --b output/coding_matrix_b.csv

输出：
    output/reliability.csv       指标表
    output/disagreements.csv     分歧明细

仅依赖标准库。
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


def load_matrix(path: Path) -> tuple[list[str], list[str], dict[str, dict[str, int]]]:
    """返回 (文档列表, 子工具列表, {文件名: {子工具: 0/1}})。"""
    with path.open(encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        rows = list(reader)

    docs = [r["文件名"] for r in rows]
    subs = [f for f in fields if f not in ("文件名", "字符数", "总词次", "命中子工具数")]
    matrix: dict[str, dict[str, int]] = {}
    for r in rows:
        matrix[r["文件名"]] = {
            s: 1 if str(r.get(s, "0")).strip() in ("1", "1.0", "True", "true") else 0
            for s in subs
        }
    return docs, subs, matrix


def build_units(
    a: dict[str, dict[str, int]],
    b: dict[str, dict[str, int]],
    docs: list[str],
    subs: list[str],
) -> dict[tuple[str, str], list[str]]:
    """判定单元 = 文档 × 子工具，值为两名编码员的 0/1。"""
    units = {}
    for d in docs:
        for s in subs:
            units[(d, s)] = [str(a.get(d, {}).get(s, 0)), str(b.get(d, {}).get(s, 0))]
    return units


def percent_agreement(units: dict[tuple, list[str]]) -> float:
    if not units:
        return float("nan")
    return sum(1 for v in units.values() if len(set(v)) == 1) / len(units)


def krippendorff_alpha(units: dict[tuple, list[str]]) -> float:
    """名义尺度 α，支持 2 名以上编码员与缺失值。"""
    usable = {k: v for k, v in units.items() if len([x for x in v if x != ""]) >= 2}
    if not usable:
        return float("nan")

    total = 0
    observed = 0.0
    for vals in usable.values():
        vals = [x for x in vals if x != ""]
        m = len(vals)
        total += m
        counts = Counter(vals)
        observed += sum(c * (m - c) for c in counts.values()) / (m - 1)

    do = observed / total
    all_vals = [x for vals in usable.values() for x in vals if x != ""]
    n = len(all_vals)
    if n < 2:
        return float("nan")
    counts = Counter(all_vals)
    de = (n * n - sum(c * c for c in counts.values())) / (n * (n - 1))
    if de == 0:
        return 1.0 if do == 0 else float("nan")
    return 1 - do / de


def cohen_kappa(units: dict[tuple, list[str]]) -> float:
    usable = {k: v for k, v in units.items() if len(v) == 2 and "" not in v}
    if not usable:
        return float("nan")
    n = len(usable)
    po = sum(1 for v in usable.values() if v[0] == v[1]) / n
    c1 = Counter(v[0] for v in usable.values())
    c2 = Counter(v[1] for v in usable.values())
    pe = sum((c1[k] / n) * (c2[k] / n) for k in set(c1) | set(c2))
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else float("nan")
    return (po - pe) / (1 - pe)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    root = here.parent

    ap = argparse.ArgumentParser(description="编码信度检验")
    ap.add_argument("--a", required=True, help="编码员 A 的 0/1 矩阵 CSV")
    ap.add_argument("--b", required=True, help="编码员 B 的 0/1 矩阵 CSV")
    ap.add_argument("--out", default=str(root / "output"), help="输出目录")
    args = ap.parse_args(argv)

    pa, pb = Path(args.a), Path(args.b)
    for p in (pa, pb):
        if not p.exists():
            print(f"文件不存在：{p}", file=sys.stderr)
            return 1

    docs_a, subs_a, mat_a = load_matrix(pa)
    docs_b, subs_b, mat_b = load_matrix(pb)

    docs = sorted(set(docs_a) | set(docs_b))
    subs = [s for s in subs_a if s in subs_b]
    missing = [s for s in subs_a if s not in subs_b]
    if missing:
        print(f"警告：B 缺少子工具列 {missing}，已忽略", file=sys.stderr)

    units = build_units(mat_a, mat_b, docs, subs)
    pa_val = percent_agreement(units)
    alpha = krippendorff_alpha(units)
    kappa = cohen_kappa(units)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rel_path = out_dir / "reliability.csv"
    with rel_path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["指标", "取值", "判定单元数", "说明"])
        w.writerow(["percent_agreement", f"{pa_val:.3f}", len(units), "简单一致率"])
        w.writerow(["krippendorff_alpha", f"{alpha:.3f}" if alpha == alpha else "nan",
                    len(units), "名义尺度；α ≥ 0.80 视为可靠"])
        w.writerow(["cohen_kappa", f"{kappa:.3f}" if kappa == kappa else "nan",
                    len(units), "仅两名编码员"])

    disagree_path = out_dir / "disagreements.csv"
    diffs = [{"文档": k[0], "子工具": k[1], "编码员A": v[0], "编码员B": v[1]}
             for k, v in units.items() if len(set(v)) > 1]
    with disagree_path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["文档", "子工具", "编码员A", "编码员B"])
        w.writeheader()
        w.writerows(diffs)

    print(f"判定单元：{len(units)}（{len(docs)} 篇 × {len(subs)} 个子工具）")
    print(f"一致率           : {pa_val:.3f}")
    print(f"Krippendorff α   : {alpha:.3f}" if alpha == alpha else "Krippendorff α   : nan")
    print(f"Cohen κ          : {kappa:.3f}" if kappa == kappa else "Cohen κ          : nan")
    print(f"分歧单元         : {len(diffs)} 个")
    print(f"\n已输出：{rel_path.name} / {disagree_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
