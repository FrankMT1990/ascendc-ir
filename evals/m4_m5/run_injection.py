# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""M4/M5 注入集测量入口。

- 合法样本：期望零 block 诊断（M4 误拒）。
- 注入样本：期望规则集合被触发（M4 召回）；诊断 callsite 的文件与源码行片段
  命中金标（M5 定位，对齐 ADR 0006 的「file + 源码行片段」）。
- 另报干净率：实际诊断 ID 集合 == 期望集合（一处改动、一套规则）。

用法：python evals/m4_m5/run_injection.py
"""

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ascendc_ir.verify import verify  # noqa: E402

SET_DIR = Path(__file__).resolve().parent


def single_point_shortfall(injected: list) -> dict:
    """每条已测规则至少 3 个单点样本。expect_ids 必须恰好是这一条规则。

    多规则样本里的出现次数不算单点。V008 在 2201 设备表落地前不计入。
    """
    rules = {rule for item in injected for rule in item["expect_ids"] if rule != "V008"}
    counts = Counter(
        item["expect_ids"][0] for item in injected if len(item.get("expect_ids") or []) == 1
    )
    return {rule: counts[rule] for rule in sorted(rules) if counts[rule] < 3}


def load_sample(path: Path, attr: str = "SAMPLE"):
    spec = importlib.util.spec_from_file_location(path.stem + "_" + attr, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, attr)
    return fn.trace()


def main() -> int:
    gold = json.loads((SET_DIR / "gold.json").read_text(encoding="utf-8"))

    legal_ok = 0
    for rel in gold["legal"]:
        diags = verify(load_sample(SET_DIR / rel))
        blocks = [d for d in diags if d.severity == "block"]
        if blocks:
            print(f"[误拒] {rel}: {[(d.id, d.message) for d in blocks]}")
        else:
            legal_ok += 1

    recall = 0
    located = 0
    clean = 0
    for item in gold["injected"]:
        diags = verify(load_sample(SET_DIR / item["file"], item.get("attr", "SAMPLE")))
        actual_ids = sorted({d.id for d in diags})
        expect_ids = sorted(item["expect_ids"])
        hits = [d for d in diags if d.id in expect_ids]

        if set(expect_ids) <= set(actual_ids):
            recall += 1
        else:
            print(f"[漏检] {item['file']}: 期望 {expect_ids}，实际 {actual_ids}")

        located_hit = any(
            item["gold_line_contains"] in d.callsite.statement
            and Path(d.callsite.file).name == Path(item["file"]).name
            for d in hits
        )
        if located_hit:
            located += 1
        elif hits:
            print(f"[定位偏] {item['file']}: {hits[0].callsite.statement!r} 不含 {item['gold_line_contains']!r}")

        if actual_ids == expect_ids:
            clean += 1
        else:
            print(f"[不干净] {item['file']}: 期望 {expect_ids}，实际 {actual_ids}")

    n_legal = len(gold["legal"])
    n_injected = len(gold["injected"])
    print(f"合法样本零误拒: {legal_ok}/{n_legal}")
    print(f"注入召回: {recall}/{n_injected}")
    print(f"定位命中: {located}/{n_injected}")
    print(f"诊断干净: {clean}/{n_injected}")
    # 唯一通过线（与 docs/evaluation/metrics.md 一致）：误拒=0、召回≥0.9、定位≥0.8、干净率=100%
    ok = (
        legal_ok == n_legal
        and recall / n_injected >= 0.9
        and located / n_injected >= 0.8
        and clean == n_injected
    )
    class_ok = True
    for name, rule_id in gold["classes"].items():
        subset = [item for item in gold["injected"] if item["expect_ids"] == [rule_id]]
        if len(subset) < 3:
            print(f"[类不足] {name} {rule_id}: {len(subset)} < 3")
            class_ok = False
            continue
        hit = 0
        for item in subset:
            diags = verify(load_sample(SET_DIR / item["file"], item.get("attr", "SAMPLE")))
            actual = {d.id for d in diags}
            if rule_id in actual:
                hit += 1
        ratio = hit / len(subset)
        print(f"类召回 {name} {rule_id}: {hit}/{len(subset)}")
        if ratio < 0.9:
            class_ok = False
    short = single_point_shortfall(gold["injected"])
    measured_ok = not short
    if not measured_ok:
        print(f"[规则单点注入不足 3] {short}")
    independent = gold.get("independent") or []
    if not independent:
        print("[缺独立故障集]")
    else:
        for rel in independent:
            diags = verify(load_sample(SET_DIR / rel))
            print(f"[独立故障] {rel}: {sorted({d.id for d in diags})}")
    discipline = class_ok and measured_ok and bool(independent)
    if not ok:
        print("M4/M5 注入集: FAIL")
        return 1
    if not discipline:
        print("旧集回归通过，C3 未测")
        return 2
    print("M4/M5 注入集: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
