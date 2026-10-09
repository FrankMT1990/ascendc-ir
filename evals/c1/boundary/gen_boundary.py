"""C1 第 3 步：边界组必测输入与 golden 生成（确定性，无随机）。

每组用写死的边界值 pattern 循环铺满任务计时 shape；golden 按 cann-bench refs
在 NPU 上计算。输出哈希写入 boundary_inputs_hashes.json。本脚本与封存的输入
哈希、refs commit 共同构成 golden 的可复现定义（大张量 golden 不直接入 git，
gelu golden 为 268MB）。
"""

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ASCEND_LAUNCH_MODE", "ACL")

BENCH = Path("/home/w00964611/cann-bench")
OUT = Path("/home/w00964611/c1_boundary")


def sha256_tensor(t) -> str:
    return hashlib.sha256(t.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tile_pattern(pattern, numel):
    import torch

    reps = (numel + len(pattern) - 1) // len(pattern)
    flat = torch.tensor(pattern, dtype=torch.float32).repeat(reps)[:numel]
    return flat


def tile_mask(numel):
    import torch

    return torch.tensor([0, 1], dtype=torch.uint8).repeat(numel // 2)


def main():
    import torch
    import torch_npu
    from torch_npu.dynamo import torchair as _ti

    sys.modules.setdefault("torchair", _ti)
    torch.npu.set_device(0)

    refs_mod = load("cb_refs", BENCH / "scripts/baseline/refs/level1.py")

    OUT.mkdir(parents=True, exist_ok=True)
    out = {}

    def seal(task_id, inputs_cpu, golden_fn, note):
        args_np = [t.npu() for t in inputs_cpu]
        golden = golden_fn(*args_np)
        torch.npu.synchronize()
        golden_cpu = golden.cpu()
        out[task_id] = {
            "inputs_sha256": [sha256_tensor(t) for t in inputs_cpu],
            "golden_sha256": sha256_tensor(golden_cpu),
            "golden_dtype": str(golden_cpu.dtype),
            "golden_shape": list(golden_cpu.shape),
            "note": note,
        }
        print(task_id, out[task_id]["golden_sha256"][:16], flush=True)

    N4 = 2048 * 2048
    NG = 8192 * 8192

    # exp_f32 边界：范围端点、零、中间值
    x = tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], N4).reshape(2048, 2048)
    seal("exp_f32", [x], lambda t: refs_mod.exp_ref([t], {"base": -1.0, "scale": 1.5, "shift": 0.0}).cpu(),
         "boundary pattern [-2,-1,-0.5,0,0.5,1,2] tiled over [2048,2048]")

    # sigmoid_f32 边界
    x = tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], N4).reshape(2048, 2048)
    seal("sigmoid_f32", [x], lambda t: refs_mod.sigmoid_ref([t], {}).cpu(),
         "boundary pattern [-2,-1,-0.5,0,0.5,1,2] tiled")

    # gelu_f32 边界：tanh 饱和区、拐点、端点
    x = tile_pattern([-100.0, -20.0, -3.0, -0.5, 0.0, 0.5, 3.0, 20.0, 100.0], NG).reshape(8192, 8192)
    seal("gelu_f32", [x], lambda t: refs_mod.gelu_ref([t], {"approximate": "tanh"}).cpu(),
         "boundary pattern [-100,-20,-3,-0.5,0,0.5,3,20,100] tiled over [8192,8192]")

    # mish_f32 边界
    x = tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], N4).reshape(2048, 2048)
    seal("mish_f32", [x], lambda t: refs_mod.mish_ref([t], {}).cpu(),
         "boundary pattern [-2,-1,-0.5,0,0.5,1,2] tiled")

    # masked_scale_f32 边界：x 边界 × mask 全 0/1 交替
    x = tile_pattern([-2.0, -1.0, 0.0, 1.0, 2.0], N4).reshape(2048, 2048)
    m = tile_mask(N4).reshape(2048, 2048)
    seal("masked_scale_f32", [x, m], lambda t, mk: refs_mod.masked_scale_ref([t, mk], {"scale": 1.0}).cpu(),
         "x boundary [-2,-1,0,1,2]; mask alternating 0/1 (uint8, 2-element aligned)")

    # swi_glu_f32 边界（pattern 铺满 [2048,4096]，x0/x1 均覆盖）
    x = tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], 2048 * 4096).reshape(2048, 4096)
    seal("swi_glu_f32", [x], lambda t: refs_mod.swi_glu_ref([t], {"dim": -1}).cpu(),
         "boundary pattern tiled over [2048,4096]")

    # foreach_addcdiv_f32 边界：除数下界为主
    x1 = tile_pattern([-1.0, -0.5, 0.0, 0.5, 1.0], 2 * 1024 * 1024).reshape(2, 1024, 1024)
    x2 = tile_pattern([-1.0, -0.5, 0.0, 0.5, 1.0], 2 * 1024 * 1024).reshape(2, 1024, 1024)
    x3 = tile_pattern([0.5, 0.75, 1.0], 2 * 1024 * 1024).reshape(2, 1024, 1024)

    def foreach_golden(a, b, c):
        res = refs_mod.foreach_addcdiv_scalar_ref(
            [[a[0], a[1]], [b[0], b[1]], [c[0], c[1]]], {"scalar": 1.0})
        return torch.cat([t.reshape(1, -1) for t in res], dim=0).reshape(2, 1024, 1024).cpu()

    seal("foreach_addcdiv_f32", [x1, x2, x3], foreach_golden,
         "x1/x2 boundary [-1,-0.5,0,0.5,1]; x3 divisor boundary [0.5,0.75,1.0]")

    (OUT / "boundary_inputs_hashes.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("BOUNDARY_ALL_DONE")


if __name__ == "__main__":
    main()
