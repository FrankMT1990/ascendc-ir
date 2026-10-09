"""C1 第 2/3 步：T_HW 下界核计时 + 计时输入/golden 哈希封存素材。

与 T_baseline 完全同一计时入口：cann-bench PerfEvaluator（ACL launch +
msprof kernel_details.csv、MsProfSummaryStrategy、warmup 5、repeat 20）。
输入由 cann-bench inputs.build_inputs 以同 case_id 生成，数值与 T_baseline
采集时同一组。
"""

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ASCEND_LAUNCH_MODE", "ACL")

BENCH = Path("/home/w00964611/cann-bench")
OUT = Path("/home/w00964611/c1_hw")


def sha256_tensor(t) -> str:
    import torch

    return hashlib.sha256(t.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def pack_mask_bits(mask_u8):
    """board_3510 select 掩码位打包：偶数元素低 4bit、奇数元素高 4bit，每字节 2 元素。"""
    import torch

    n = mask_u8.numel()
    m = mask_u8.to(torch.uint8).reshape(-1)
    packed = torch.zeros(n // 2, dtype=torch.uint8)
    packed |= (m[0::2] & 0x01) << 0
    packed |= (m[1::2] & 0x01) << 4
    return packed


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    import torch
    import torch_npu
    from torch_npu.dynamo import torchair as _ti

    sys.modules.setdefault("torchair", _ti)
    torch.npu.set_device(0)

    inputs_mod = load("cb_inputs", BENCH / "scripts/baseline/inputs.py")
    refs_mod = load("cb_refs", BENCH / "scripts/baseline/refs/level1.py")
    cb = load("cb_collect", BENCH / "scripts/collect_baseline.py")

    sys.path.insert(0, str(BENCH))
    from kernel_eval.config import Config

    bench_root = BENCH / "tasks"
    config = Config(
        device_type="npu",
        device_id=0,
        enable_profiler=True,
        profiler_level="Level1",
        warmup=5,
        repeat=20,
        tasks_root=str(bench_root),
        reports_dir="/home/w00964611/c1_reports",
        torch_op_guard_mode="off",
        enable_accuracy_retry=False,
        eval_seed=0,
        enable_acl_launch_mode=True,
        enable_msprof_export=True,
        perf_metric_strategy_override="msprof_summary",
    )
    collector = cb.BaselineCollector(config=config, bench_root=bench_root, warmup=5, repeat=20)

    import c1hw  # pack 构建出的 torch ops

    OUT.mkdir(parents=True, exist_ok=True)
    hashes = {}
    timing = {}

    def finish(task_id, op_name, args_np, inputs_for_hash, golden_fn, extra_note=None):
        # golden（NPU 上按 refs 同实现计算）
        golden = golden_fn()
        torch.npu.synchronize()
        rec = {
            "task": task_id,
            "inputs_sha256": {k: sha256_tensor(v) for k, v in inputs_for_hash.items()},
            "golden_sha256": sha256_tensor(golden),
            "golden_dtype": str(golden.dtype),
            "golden_shape": list(golden.shape),
        }
        if extra_note:
            rec["note"] = extra_note
        hashes[task_id] = rec

        def fn(*a):
            return getattr(torch.ops.c1hw, op_name)(*a)

        _, perf = collector.perf_evaluator.run_profiled(f"c1hw_{task_id}_hw", fn, *args_np)
        if perf.error_msg or perf.elapsed_us <= 0:
            timing[task_id] = {"t_hw_us": None, "error": perf.error_msg or "no_csv"}
        else:
            timing[task_id] = {
                "t_hw_us": perf.elapsed_us,
                "device_kernels": perf.op_times.get("device_kernels", {}),
                "data_source": perf.metadata.get("data_source"),
            }
        print(task_id, json.dumps(timing[task_id])[:200], flush=True)

    # exp_f32: case 2
    (x,) = inputs_mod.build_inputs([[2048, 2048]], ["float32"], [-2, 2], 2, "level1/exp")
    x_np = x.npu()
    finish(
        "exp_f32",
        "floor_exp",
        (x_np,),
        {"x": x},
        lambda: refs_mod.exp_ref([x_np], {"base": -1.0, "scale": 1.5, "shift": 0.0}).cpu(),
    )

    # sigmoid_f32: case 2
    (x,) = inputs_mod.build_inputs([[2048, 2048]], ["float32"], [-2, 2], 2, "level1/sigmoid")
    x_np = x.npu()
    finish(
        "sigmoid_f32",
        "floor_sigmoid",
        (x_np,),
        {"x": x},
        lambda: refs_mod.sigmoid_ref([x_np], {}).cpu(),
    )

    # gelu_f32: case 5
    (x,) = inputs_mod.build_inputs([[8192, 8192]], ["float32"], [-100, 100], 5, "level1/gelu")
    x_np = x.npu()
    finish(
        "gelu_f32",
        "floor_gelu",
        (x_np,),
        {"x": x},
        lambda: refs_mod.gelu_ref([x_np], {"approximate": "tanh"}).cpu(),
    )

    # mish_f32: case 2
    (x,) = inputs_mod.build_inputs([[2048, 2048]], ["float32"], [-2, 2], 2, "level1/mish")
    x_np = x.npu()
    finish(
        "mish_f32",
        "floor_mish",
        (x_np,),
        {"x": x},
        lambda: refs_mod.mish_ref([x_np], {}).cpu(),
    )

    # masked_scale_f32: case 2（x f32 + mask uint8，掩码按 select 形态位打包）
    x, mask = inputs_mod.build_inputs(
        [[2048, 2048], [2048, 2048]], ["float32", "uint8"], [[-2, 2], [0, 1]], 2, "level1/masked_scale"
    )
    packed = pack_mask_bits(mask)
    assert packed.numel() == x.numel() * 4 // 8
    x_np, mask_np = x.npu(), packed.npu()
    finish(
        "masked_scale_f32",
        "floor_masked_scale",
        (x_np, mask_np),
        {"x": x, "mask_packed_u8": packed},
        lambda: refs_mod.masked_scale_ref([x_np, mask.npu()], {"scale": 1.0}).cpu(),
        extra_note="mask 位打包为 select 形态（每字节 2 元素 4bit）；golden 用原始 uint8 mask 按 refs 计算",
    )

    # swi_glu_f32: case 2
    (x,) = inputs_mod.build_inputs([[2048, 4096]], ["float32"], [-2, 2], 2, "level1/swi_glu")
    x_np = x.npu()
    finish(
        "swi_glu_f32",
        "floor_swi_glu",
        (x_np,),
        {"x": x},
        lambda: refs_mod.swi_glu_ref([x_np], {"dim": -1}).cpu(),
    )

    # foreach_addcdiv_f32: case 1（3 输入各 2 tensor；下界核用 cat 连续视角）
    x1l, x2l, x3l = inputs_mod.build_inputs(
        [[[1024, 1024], [1024, 1024]], [[1024, 1024], [1024, 1024]], [[1024, 1024], [1024, 1024]]],
        ["float32", "float32", "float32"],
        [[-1.0, 1.0], [-1.0, 1.0], [0.5, 1.0]],
        1,
        "level1/foreach_addcdiv_scalar",
    )
    x1c = torch.cat([t.reshape(1, -1) for t in x1l], dim=0).reshape(2, 1024, 1024)
    x2c = torch.cat([t.reshape(1, -1) for t in x2l], dim=0).reshape(2, 1024, 1024)
    x3c = torch.cat([t.reshape(1, -1) for t in x3l], dim=0).reshape(2, 1024, 1024)
    x1np, x2np, x3np = x1c.npu(), x2c.npu(), x3c.npu()
    finish(
        "foreach_addcdiv_f32",
        "floor_foreach_addcdiv",
        (x1np, x2np, x3np),
        {"x1_cat": x1c, "x2_cat": x2c, "x3_cat": x3c},
        lambda: torch.cat(
            [
                t.reshape(1, -1)
                for t in refs_mod.foreach_addcdiv_scalar_ref(
                    [[x1np[0], x1np[1]], [x2np[0], x2np[1]], [x3np[0], x3np[1]]], {"scalar": 1.0}
                )
            ],
            dim=0,
        )
        .reshape(2, 1024, 1024)
        .cpu(),
        extra_note="下界核输入为 cat 连续视角（数值与独立 tensor 列表逐元素一致）；golden 按 refs 独立列表计算后同样 cat",
    )

    (OUT / "inputs_golden_hashes.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (OUT / "hw_floor_timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("TIMING_ALL_DONE")


if __name__ == "__main__":
    main()
