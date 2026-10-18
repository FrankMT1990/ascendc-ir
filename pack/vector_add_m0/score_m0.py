#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M0 判分脚本（manifest v1.2）：只读评测归档的原始 kernel_details.csv。

规则（docs/evaluation/metrics.md）：
- 排除 warmup 保留名（CannBenchWarmup / CannBenchCacheClean；回退匹配 MatMulV3/ReduceMax 的 warmup shape）
- 目标行：Name 含 add_custom 且非 warmup
- 以 CannBenchCacheClean 行为 step 分隔；每个分隔后的段为一个测量 step，段内目标行时长求和
- 统计量：跨 step 取中位（不用最小值）
用法：python3 score_m0.py <kernel_details.csv> [<kernel_details.csv> ...]
"""
import csv
import statistics
import sys

WARMUP_TOKENS = ("CannBenchWarmup", "CannBenchCacheClean")
WARMUP_MATMUL_SHAPE = '"10240,10240;10240,10240"'
WARMUP_REDUCE_SHAPE = '"96,1024,1024;3"'
TARGET_TOKEN = "add_custom"


def is_warmup(op_type: str, input_shapes: str) -> bool:
    if not op_type:
        return False
    for token in WARMUP_TOKENS:
        if token in op_type:
            return True
    if not input_shapes:
        return False
    if op_type == "MatMulV3" and WARMUP_MATMUL_SHAPE in input_shapes:
        return True
    if op_type == "ReduceMax" and WARMUP_REDUCE_SHAPE in input_shapes:
        return True
    return False


def score(csv_path: str) -> dict:
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty csv: {csv_path}")

    warmup_idx = [i for i, r in enumerate(rows)
                  if is_warmup((r.get("Type") or "").strip(), (r.get("Input Shapes") or "").strip())]
    if not warmup_idx:
        raise SystemExit(f"no cache-clean delimiters found (freq_boost off?): {csv_path}")

    # 分隔符之间的段 = 一个测量 step；段内目标行求和
    step_totals = []
    target_names = set()
    for si, wi in enumerate(warmup_idx):
        lo = wi + 1
        hi = warmup_idx[si + 1] if si + 1 < len(warmup_idx) else len(rows)
        total, n = 0.0, 0
        for r in rows[lo:hi]:
            name = (r.get("Name") or (r.get("Type") or "")).strip()
            op_type = (r.get("Type") or "").strip()
            shapes = (r.get("Input Shapes") or "").strip()
            if not name or is_warmup(op_type, shapes):
                continue
            if TARGET_TOKEN not in name:
                continue  # 非目标 kernel（如框架辅助 kernel）——按名称过滤
            try:
                dur = float((r.get("Duration(us)") or "0").strip())
            except ValueError:
                continue
            if dur <= 0:
                continue
            total += dur
            n += 1
            target_names.add(f"{name} | {shapes[:60]}")
        if n:
            step_totals.append(total)

    if not step_totals:
        raise SystemExit(f"no target rows ({TARGET_TOKEN}) in {csv_path}")
    med = statistics.median(step_totals)
    return {
        "csv": csv_path,
        "steps_measured": len(step_totals),
        "per_step_totals_us": [round(t, 3) for t in step_totals],
        "median_us": round(med, 3),
        "target_names": sorted(target_names),
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for p in sys.argv[1:]:
        r = score(p)
        print(f"csv: {r['csv']}")
        print(f"  measured steps: {r['steps_measured']}")
        print(f"  per-step totals (us): {r['per_step_totals_us']}")
        print(f"  MEDIAN (us): {r['median_us']}")
        print(f"  target rows: {r['target_names']}")


if __name__ == "__main__":
    main()
