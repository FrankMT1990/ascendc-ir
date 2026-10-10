"""C1 数值门：必测输入/golden 的确定性再生、封存哈希核对与容差比较。

计时组：cann-bench inputs.build_inputs（seed=0xC0FFEE+case_id*31337），数值与
T_baseline 采集时同一组。边界组：边界值 pattern 确定性铺格（gen_boundary.py 同
逻辑）。golden 按 cann-bench refs 计算。比较式逐元素 abs(a-b) <= atol+rtol*abs(b)。
"""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import torch

BENCH = Path("/home/w00964611/cann-bench")
REPO_HASHES = Path(__file__).resolve().parents[3] / "evals" / "c1"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_inputs_mod = _load("cb_inputs", BENCH / "scripts/baseline/inputs.py")
_refs_mod = _load("cb_refs", BENCH / "scripts/baseline/refs/level1.py")

TOL = json.loads((REPO_HASHES / "tolerance.json").read_text(encoding="utf-8"))
ATOL, RTOL = TOL["atol"], TOL["rtol"]
TIMING_HASHES = json.loads((REPO_HASHES / "timing/inputs_golden_hashes.json").read_text(encoding="utf-8"))
BOUNDARY_HASHES = json.loads((REPO_HASHES / "boundary/boundary_inputs_hashes.json").read_text(encoding="utf-8"))


def sha256_tensor(t) -> str:
    return hashlib.sha256(t.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def _tile_pattern(pattern, numel):
    reps = (numel + len(pattern) - 1) // len(pattern)
    return torch.tensor(pattern, dtype=torch.float32).repeat(reps)[:numel]


def _tile_mask(numel):
    return torch.tensor([0, 1], dtype=torch.uint8).repeat(numel // 2)


def pack_mask_bits(mask_u8):
    n = mask_u8.numel()
    m = mask_u8.to(torch.uint8).reshape(-1)
    packed = torch.zeros(n // 2, dtype=torch.uint8)
    packed |= (m[0::2] & 0x01) << 0
    packed |= (m[1::2] & 0x01) << 4
    return packed


N4 = 2048 * 2048
NG = 8192 * 8192
NF = 2 * 1024 * 1024


def build_timing_inputs():
    """计时组：返回 {task: (args_list_cpu, golden_cpu)}。args 为内核签名顺序的 CPU tensor。"""
    out = {}

    (x,) = _inputs_mod.build_inputs([[2048, 2048]], ["float32"], [-2, 2], 2, "level1/exp")
    out["exp_f32"] = ([x], _refs_mod.exp_ref([x.npu()], {"base": -1.0, "scale": 1.5, "shift": 0.0}).cpu())

    (x,) = _inputs_mod.build_inputs([[2048, 2048]], ["float32"], [-2, 2], 2, "level1/sigmoid")
    out["sigmoid_f32"] = ([x], _refs_mod.sigmoid_ref([x.npu()], {}).cpu())

    (x,) = _inputs_mod.build_inputs([[8192, 8192]], ["float32"], [-100, 100], 5, "level1/gelu")
    out["gelu_f32"] = ([x], _refs_mod.gelu_ref([x.npu()], {"approximate": "tanh"}).cpu())

    (x,) = _inputs_mod.build_inputs([[2048, 2048]], ["float32"], [-2, 2], 2, "level1/mish")
    out["mish_f32"] = ([x], _refs_mod.mish_ref([x.npu()], {}).cpu())

    x, m = _inputs_mod.build_inputs(
        [[2048, 2048], [2048, 2048]], ["float32", "uint8"], [[-2, 2], [0, 1]], 2, "level1/masked_scale")
    packed = pack_mask_bits(m)
    out["masked_scale_f32"] = ([x, packed], _refs_mod.masked_scale_ref([x.npu(), m.npu()], {"scale": 1.0}).cpu())

    (x,) = _inputs_mod.build_inputs([[2048, 4096]], ["float32"], [-2, 2], 2, "level1/swi_glu")
    out["swi_glu_f32"] = ([x], _refs_mod.swi_glu_ref([x.npu()], {"dim": -1}).cpu())

    x1l, x2l, x3l = _inputs_mod.build_inputs(
        [[[1024, 1024], [1024, 1024]], [[1024, 1024], [1024, 1024]], [[1024, 1024], [1024, 1024]]],
        ["float32", "float32", "float32"],
        [[-1.0, 1.0], [-1.0, 1.0], [0.5, 1.0]],
        1, "level1/foreach_addcdiv_scalar")
    x1 = torch.cat([t.reshape(1, -1) for t in x1l], dim=0).reshape(2, 1024, 1024)
    x2 = torch.cat([t.reshape(1, -1) for t in x2l], dim=0).reshape(2, 1024, 1024)
    x3 = torch.cat([t.reshape(1, -1) for t in x3l], dim=0).reshape(2, 1024, 1024)
    g = torch.cat([t.reshape(1, -1) for t in _refs_mod.foreach_addcdiv_scalar_ref(
        [[x1.npu()[0], x1.npu()[1]], [x2.npu()[0], x2.npu()[1]], [x3.npu()[0], x3.npu()[1]]],
        {"scalar": 1.0})], dim=0).reshape(2, 1024, 1024).cpu()
    out["foreach_addcdiv_f32"] = ([x1, x2, x3], g)

    return out


def build_boundary_inputs():
    """边界组：确定性边界值铺格（与 evals/c1/boundary/gen_boundary.py 同逻辑）。"""
    out = {}

    x = _tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], N4).reshape(2048, 2048)
    out["exp_f32"] = ([x], _refs_mod.exp_ref([x.npu()], {"base": -1.0, "scale": 1.5, "shift": 0.0}).cpu())

    x = _tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], N4).reshape(2048, 2048)
    out["sigmoid_f32"] = ([x], _refs_mod.sigmoid_ref([x.npu()], {}).cpu())

    x = _tile_pattern([-100.0, -20.0, -3.0, -0.5, 0.0, 0.5, 3.0, 20.0, 100.0], NG).reshape(8192, 8192)
    out["gelu_f32"] = ([x], _refs_mod.gelu_ref([x.npu()], {"approximate": "tanh"}).cpu())

    x = _tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], N4).reshape(2048, 2048)
    out["mish_f32"] = ([x], _refs_mod.mish_ref([x.npu()], {}).cpu())

    x = _tile_pattern([-2.0, -1.0, 0.0, 1.0, 2.0], N4).reshape(2048, 2048)
    m = _tile_mask(N4).reshape(2048, 2048)
    out["masked_scale_f32"] = ([x, pack_mask_bits(m)],
                                _refs_mod.masked_scale_ref([x.npu(), m.npu()], {"scale": 1.0}).cpu(),
                                [x, m])  # 哈希对象用原始 uint8 mask（与封存记录一致），执行参数用 packed

    x = _tile_pattern([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0], 2048 * 4096).reshape(2048, 4096)
    out["swi_glu_f32"] = ([x], _refs_mod.swi_glu_ref([x.npu()], {"dim": -1}).cpu())

    x1 = _tile_pattern([-1.0, -0.5, 0.0, 0.5, 1.0], NF).reshape(2, 1024, 1024)
    x2 = _tile_pattern([-1.0, -0.5, 0.0, 0.5, 1.0], NF).reshape(2, 1024, 1024)
    x3 = _tile_pattern([0.5, 0.75, 1.0], NF).reshape(2, 1024, 1024)

    def _g(a, b, c):
        an, bn, cn = a.npu(), b.npu(), c.npu()
        res = _refs_mod.foreach_addcdiv_scalar_ref(
            [[an[0], an[1]], [bn[0], bn[1]], [cn[0], cn[1]]], {"scalar": 1.0})
        return torch.cat([t.reshape(1, -1) for t in res], dim=0).reshape(2, 1024, 1024).cpu()

    out["foreach_addcdiv_f32"] = ([x1, x2, x3], _g(x1, x2, x3))

    return out


def verify_hashes(task_id, args, golden, group):
    """再生结果与封存哈希核对；任一不符返回 False（该侧未测）。"""
    rec = (TIMING_HASHES if group == "timing" else BOUNDARY_HASHES)[task_id]
    keys = sorted(rec["inputs_sha256"]) if isinstance(rec["inputs_sha256"], dict) else None
    if keys is not None:
        got = {k: sha256_tensor(v) for k, v in zip(rec["inputs_sha256"].keys(), args)}
        for k in rec["inputs_sha256"]:
            if got[k] != rec["inputs_sha256"][k]:
                return False
    else:
        got = [sha256_tensor(v) for v in args]
        if got != rec["inputs_sha256"]:
            return False
    return sha256_tensor(golden) == rec["golden_sha256"]


def compare(output, golden, atol=ATOL, rtol=RTOL):
    """逐元素 abs(a-b) <= atol+rtol*abs(b)；NaN/形状/dtype 不一致即失败。"""
    a = output.detach().cpu()
    b = golden.detach().cpu()
    if a.dtype != b.dtype or a.numel() != b.numel():
        return False, "dtype_or_numel_mismatch"
    if torch.isnan(a).any():
        return False, "nan_in_output"
    diff = (a.double() - b.double()).abs()
    limit = atol + rtol * b.double().abs()
    bad = int((diff > limit).sum())
    if bad:
        idx = (diff > limit).nonzero()[0]
        i = int(idx[0]) if idx.numel() else 0
        return False, f"{bad} violations, first at {i}: |{a.flatten()[i]:.6g}-{b.flatten()[i]:.6g}| > {limit.flatten()[i]:.6g}"
    return True, "ok"
