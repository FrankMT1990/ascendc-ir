"""C1 扫描脚本自测：反例必须全部命中，正例必须全部通过。

输出 selftest_result.json（随协议封存）。退出码 0 = 自测通过。
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"

IR_EXPECT_HIT = [
    "ir_bad_literal.py",
    "ir_bad_eval.py",
    "ir_bad_concat.py",
    "ir_bad_ascfile.py",
    "ir_bad_cstring.py",
    "ir_bad_getattr.py",
]
IR_EXPECT_PASS = [
    "ir_ok_add.py",
    "ir_ok_chain.py",
    "ir_ok_compute.py",
]
CTL_EXPECT_HIT = [
    "ctl_bad_cube.asc",
    "ctl_bad_multicore.asc",
    "ctl_bad_offlist.asc",
    "ctl_bad_multicore.cpp",
]
CTL_EXPECT_PASS = [
    "ctl_ok_vector.asc",
    "ctl_ok_select.asc",
    "ctl_ok_pack.py",
]


def run(scanner: str, target: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(HERE / scanner), str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip()


def main():
    results = {"ir_escape": {}, "control_surface": {}, "consistency": {}}
    ok = True

    for f in IR_EXPECT_HIT:
        rc, out = run("ir_escape.py", CASES / f)
        hit = rc == 1
        results["ir_escape"][f] = {"expect": "hit", "rc": rc, "pass": hit, "out_tail": out.splitlines()[-2:] if out else []}
        ok &= hit
    for f in IR_EXPECT_PASS:
        rc, out = run("ir_escape.py", CASES / f)
        clean = rc == 0
        results["ir_escape"][f] = {"expect": "pass", "rc": rc, "pass": clean, "out_tail": out.splitlines()[-2:] if out else []}
        ok &= clean

    for f in CTL_EXPECT_HIT:
        rc, out = run("control_surface.py", CASES / f)
        hit = rc == 1
        results["control_surface"][f] = {"expect": "hit", "rc": rc, "pass": hit, "out_tail": out.splitlines()[-3:] if out else []}
        ok &= hit
    for f in CTL_EXPECT_PASS:
        rc, out = run("control_surface.py", CASES / f)
        clean = rc == 0
        results["control_surface"][f] = {"expect": "pass", "rc": rc, "pass": clean, "out_tail": out.splitlines()[-3:] if out else []}
        ok &= clean

    # 一致性：允许面 ⊆ 冻结支持集（catalog 集合并集）
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
    from ascendc_ir.catalog import BINARY_F32, BINARY_I32, SCALAR_F32, SCALAR_I32, SPECIAL, UNARY_F32

    support = {"asc_" + n for n in (BINARY_F32 | BINARY_I32 | SCALAR_F32 | SCALAR_I32 | UNARY_F32 | SPECIAL)}
    plumbing = {
        "asc_simd", "asc_init", "asc_get_vf_len", "asc_update_mask_b32", "asc_create_mask_b32",
        "asc_load", "asc_store", "asc_loadalign", "asc_storealign", "asc_loadalign_postupdate",
        "asc_copy_gm2ub", "asc_copy_ub2gm", "asc_sync_notify", "asc_sync_wait", "asc_sync_pipe",
        "asc_duplicate_scalar", "asc_arange",
    }
    # SPECIAL 指令的降级产物（emit.py 的 select/compare/cast/reduce helper 实际发出的 asc_* 记号）
    derived = {
        "asc_eq", "asc_eq_scalar", "asc_ge", "asc_ge_scalar", "asc_gt", "asc_gt_scalar",
        "asc_le", "asc_le_scalar", "asc_lt", "asc_lt_scalar", "asc_ne", "asc_ne_scalar",
        "asc_half2float", "asc_reduce_sum",
    }
    surface = json.loads((HERE / "allowed_surface.json").read_text(encoding="utf-8"))
    allowed = set(surface["allowed_asc_tokens"])
    off_support = sorted(allowed - support - plumbing - derived)
    results["consistency"]["allowed_minus_support"] = off_support
    results["consistency"]["derived_tokens"] = sorted(derived)
    results["consistency"]["pass"] = not off_support
    ok &= not off_support

    results["overall_pass"] = ok
    out_path = HERE / "selftest_result.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("selftest:", "PASS" if ok else "FAIL", "->", out_path)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
