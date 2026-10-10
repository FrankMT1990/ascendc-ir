"""C1 上板执行脚手架（收包 → 扫描 → 构建 → 数值门 → 计时 → 归档）。

一个 run 的处理入口。上板计法：一个任务的一个候选的完整验证流程
（两组必测输入数值门 + 通过后的计时）计 1 次上板；构建不计。

用法（fullops 环境，容器上）：
    python3 harness.py --run-id c1-pilot-1 --arm ir --package-dir /home/w00964611/pkg
"""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RUNS_ROOT = Path("/home/w00964611/c1_runs")
BENCH = Path("/home/w00964611/cann-bench")
REPO = Path(__file__).resolve().parents[3]

TASKS = ["exp_f32", "sigmoid_f32", "gelu_f32", "mish_f32",
         "masked_scale_f32", "swi_glu_f32", "foreach_addcdiv_f32"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def scan(arm: str, package_dir: Path, run_dir: Path):
    """扫描：ir_escape / control_surface。返回 {task: voided?}（按文件粒度）。"""
    script = REPO / "evals/c1/scans" / ("ir_escape.py" if arm == "ir" else "control_surface.py")
    ext = ".py" if arm == "ir" else ".asc"
    results = {}
    log_lines = []
    for f in sorted(package_dir.rglob(f"*{ext}")):
        r = subprocess.run([sys.executable, str(script), str(f)],
                           capture_output=True, text=True)
        results[f.name] = (r.returncode != 0)
        if r.returncode != 0:
            log_lines.append(r.stdout.strip())
    (run_dir / "scan.log").write_text("\n".join(log_lines), encoding="utf-8")
    return results


def build_asc_from_ir(package_dir: Path, run_dir: Path):
    """IR 臂：.py -> trace -> verify -> codegen -> .asc 文本。"""
    try:
        import tomllib  # noqa: F401
    except ModuleNotFoundError:
        import tomli as _tomli

        sys.modules["tomllib"] = _tomli
    sys.path.insert(0, str(REPO / "src"))
    from ascendc_ir.codegen import generate
    from ascendc_ir.verify import verify

    asc_by_task = {}
    errors = {}
    for f in sorted(package_dir.rglob("*.py")):
        task_id = f.stem
        if task_id not in TASKS:
            continue
        try:
            mod = load(f"c1ir_{task_id}_{hash(str(f)) & 0xffff:x}", f)
            fn = getattr(mod, task_id)
            tr = fn.trace()
            diags = verify(tr)
            if diags:
                errors[task_id] = [str(d) for d in diags]
                continue
            asc_by_task[task_id] = generate(tr)
        except Exception as e:  # noqa: BLE001
            errors[task_id] = [f"{type(e).__name__}: {e}"]
    (run_dir / "ir_verify_codegen.log").write_text(
        json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8")
    return asc_by_task, errors


def read_asc_from_ctl(package_dir: Path):
    asc_by_task = {}
    for f in sorted(package_dir.rglob("*.asc")):
        if f.stem in TASKS:
            asc_by_task[f.stem] = f.read_text(encoding="utf-8")
    return asc_by_task


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--arm", choices=["ir", "ctl"], required=True)
    ap.add_argument("--package-dir", required=True, type=Path)
    ap.add_argument("--board-budget", type=int, default=20)
    ap.add_argument("--timing", action="store_true", help="数值门全过后跑计时（kernel-only 中位）")
    args = ap.parse_args()

    import torch
    import torch_npu
    from torch_npu.dynamo import torchair as _ti
    sys.modules.setdefault("torchair", _ti)
    torch.npu.set_device(0)

    run_dir = RUNS_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": args.run_id,
        "arm": args.arm,
        "received_at": datetime.now().astimezone().isoformat(),
        "package_dir": str(args.package_dir),
        "board_budget": args.board_budget,
        "board_used": 0,
        "files": {},
        "scan": {},
        "build": {},
        "gate": {},
        "timing": {},
        "usage_record_slot": None,
    }

    # 1. 收包：文件清单 + 哈希
    for f in sorted(args.package_dir.rglob("*")):
        if f.is_file() and f.suffix in {".py", ".asc"}:
            record["files"][f.name] = {"sha256": sha256_file(f), "size": f.stat().st_size}

    # 2. 扫描
    scan_res = scan(args.arm, args.package_dir, run_dir)
    record["scan"] = scan_res
    voided = {f for f, hit in scan_res.items() if hit}

    # 3. .asc 生成/收集
    if args.arm == "ir":
        asc_by_task, verr = build_asc_from_ir(args.package_dir, run_dir)
    else:
        asc_by_task, verr = read_asc_from_ctl(args.package_dir), {}
    record["build"]["ir_errors"] = verr

    ok_tasks = {t: asc for t, asc in asc_by_task.items() if t not in verr}

    # 4. 组装 + 构建
    if ok_tasks:
        pack_dir = run_dir / "pack"
        gate_mod = load("c1_kernel_wrap", REPO / "evals/c1/runner/kernel_wrap.py")
        try:
            gate_mod.assemble_pack(ok_tasks, pack_dir)
            built, wheel = gate_mod.build_pack(pack_dir, run_dir / "build.log")
            record["build"]["ok"] = built
            record["build"]["wheel"] = str(wheel) if wheel else None
        except Exception as e:  # noqa: BLE001
            record["build"]["ok"] = False
            record["build"]["error"] = f"{type(e).__name__}: {e}"
            built = False
    else:
        built = False
        record["build"]["ok"] = False
        record["build"]["error"] = "no assemblable kernels"

    # 5. 数值门（每任务计 1 次上板）
    if built:
        import c1run  # noqa: F401  (注册 torch.ops.c1run.*)

        gate = load("c1_gate", REPO / "evals/c1/runner/inputs_gate.py")
        timing_inputs = gate.build_timing_inputs()
        boundary_inputs = gate.build_boundary_inputs()

        for t in sorted(ok_tasks):
            if args.board_budget and record["board_used"] >= args.board_budget:
                record["gate"][t] = "board_budget_exhausted"
                continue
            record["board_used"] += 1
            try:
                gate_res = {"timing": None, "boundary": None}
                all_ok = True
                for group, bundle in (("timing", timing_inputs), ("boundary", boundary_inputs)):
                    entry = bundle[t]
                    if len(entry) == 3:
                        in_cpu, golden, hash_args = entry
                    else:
                        in_cpu, golden = entry
                        hash_args = in_cpu
                    if not gate.verify_hashes(t, hash_args, golden, group):
                        gate_res[group] = "hash_mismatch(regenerated inputs differ from sealed)"
                        all_ok = False
                        break
                    args_np = [v.npu() for v in in_cpu]
                    out = getattr(torch.ops.c1run, t)(*args_np)
                    torch.npu.synchronize()
                    ok, detail = gate.compare(out, golden)
                    gate_res[group] = "pass" if ok else f"FAIL {detail}"
                    all_ok &= ok
                record["gate"][t] = gate_res
            except Exception as e:  # noqa: BLE001
                record["gate"][t] = {"error": f"{type(e).__name__}: {e}"}

        # 6. 计时（全过的任务；每组输入执行也含在每任务 1 次上板内）
        passed = [t for t in sorted(ok_tasks)
                  if isinstance(record["gate"].get(t), dict)
                  and record["gate"][t].get("timing") == "pass"
                  and record["gate"][t].get("boundary") == "pass"]
        record["passed_tasks"] = passed
        if args.timing and passed:
            cb = load("cb_collect", BENCH / "scripts/collect_baseline.py")
            sys.path.insert(0, str(BENCH))
            from kernel_eval.config import Config

            config = Config(
                device_type="npu", device_id=0, enable_profiler=True, profiler_level="Level1",
                warmup=5, repeat=20, tasks_root=str(BENCH / "tasks"),
                reports_dir="/home/w00964611/c1_reports", torch_op_guard_mode="off",
                enable_accuracy_retry=False, eval_seed=0, enable_acl_launch_mode=True,
                enable_msprof_export=True, perf_metric_strategy_override="msprof_summary")
            collector = cb.BaselineCollector(config=config, bench_root=BENCH / "tasks", warmup=5, repeat=20)
            for t in passed:
                in_cpu, _ = timing_inputs[t]

                def fn(*a, _t=t):
                    return getattr(torch.ops.c1run, _t)(*a)

                _, perf = collector.perf_evaluator.run_profiled(f"{args.run_id}_{t}", fn, *[v.npu() for v in in_cpu])
                if perf.error_msg or perf.elapsed_us <= 0:
                    record["timing"][t] = {"t_best_us": None, "error": perf.error_msg or "no_csv"}
                else:
                    record["timing"][t] = {
                        "t_best_us": perf.elapsed_us,
                        "device_kernels": perf.op_times.get("device_kernels", {}),
                        "csv_ref": "see profiler archive under c1_reports",
                    }
            record["timing_note"] = "T_best only from timing-input group (hash-verified); gate+timing together count as 1 board run per task"
    else:
        record["passed_tasks"] = []

    (run_dir / "receive_record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "passed": record.get("passed_tasks", []),
                      "board_used": record["board_used"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
