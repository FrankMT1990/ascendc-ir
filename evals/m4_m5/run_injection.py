# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""M4/M5 注入集测量入口。

合法样本：期望零 block 诊断（M4 误拒）。
注入样本：期望规则被触发（M4 召回），且诊断 callsite 源码行包含金标片段（M5 定位命中）。

用法：python evals/m4_m5/run_injection.py
"""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ascendc_ir.verify import verify  # noqa: E402

SET_DIR = Path(__file__).resolve().parent


def load_sample(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SAMPLE.trace()


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
    for item in gold["injected"]:
        diags = verify(load_sample(SET_DIR / item["file"]))
        hits = [d for d in diags if d.id == item["expect_id"]]
        if hits:
            recall += 1
            if any(item["gold_line_contains"] in d.callsite.statement for d in hits):
                located += 1
            else:
                print(f"[定位偏] {item['file']}: {hits[0].callsite.statement!r} 不含 {item['gold_line_contains']!r}")
        else:
            print(f"[漏检] {item['file']}: 期望 {item['expect_id']}，实际 {[d.id for d in diags]}")

    n_legal = len(gold["legal"])
    n_injected = len(gold["injected"])
    print(f"合法样本零误拒: {legal_ok}/{n_legal}")
    print(f"注入召回: {recall}/{n_injected}")
    print(f"定位命中: {located}/{n_injected}")
    ok = legal_ok == n_legal and recall == n_injected and located == n_injected
    print("M4/M5 注入集: PASS" if ok else "M4/M5 注入集: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
