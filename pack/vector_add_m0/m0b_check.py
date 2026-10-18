#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M0b 检查（manifest v1.2）：对已安装的 cann_bench wheel 用冻结输入组做数值判定。

比较式（claims.md v2.5.12）：逐元素 abs(a-b) <= atol + rtol*abs(b)；
a=内核输出，b=golden（CPU f32 torch.add）；atol=rtol=1e-6（开跑前写死）；
NaN / dtype / 元素个数不一致 => 失败。逐位一致率单独报告。

输入组（manifest 冻结）：
- G1 均匀：torch.manual_seed(0); x = rand(16384)*4-2; y = rand(16384)*4-2
- G2 边界：v = [0,-0,1.4e-45,-1.4e-45,1.1754944e-38,-1.1754944e-38,2,-2,1e30,-1e30]
          x = v 循环填充；y = v 错开一位循环填充

用法：python3 m0b_check.py <candidate-label>
"""
import hashlib
import sys

import torch
import torch_npu
import cann_bench

ATOL = 1e-6
RTOL = 1e-6
N = 16384
F32 = torch.int32  # 用于逐位比较的视图类型

which = sys.argv[1] if len(sys.argv) > 1 else "unknown"


def g1():
    torch.manual_seed(0)
    x = torch.rand(N) * 4 - 2
    y = torch.rand(N) * 4 - 2
    return x, y


def g2():
    v = torch.tensor(
        [0.0, -0.0, 1.4e-45, -1.4e-45, 1.1754944e-38, -1.1754944e-38, 2.0, -2.0, 1e30, -1e30],
        dtype=torch.float32)
    idx = torch.arange(N) % len(v)
    x = v[idx]
    y = v[(idx + 1) % len(v)]
    return x, y


def sha(t: torch.Tensor) -> str:
    return hashlib.sha256(t.contiguous().numpy().tobytes()).hexdigest()[:16]


def check(label, x_cpu, y_cpu):
    golden = torch.add(x_cpu, y_cpu)
    x = x_cpu.npu()
    y = y_cpu.npu()
    z = cann_bench.add(x, y)
    torch.npu.synchronize()
    a = z.cpu()
    if a.dtype != golden.dtype or a.numel() != golden.numel():
        print(f"[{which}:{label}] FAIL dtype/numel {a.dtype}/{a.numel()} vs {golden.dtype}/{golden.numel()}")
        return False, 0
    if bool(torch.isnan(a).any()):
        print(f"[{which}:{label}] FAIL NaN present")
        return False, 0
    diff = (a - golden).abs()
    tol = ATOL + RTOL * golden.abs()
    ok = bool((diff <= tol).all())
    bit = int((a.view(F32) == golden.view(F32)).sum().item())
    print(f"[{which}:{label}] tolerance_ok={ok} max_abs_diff={diff.max().item():.3e} "
          f"bit_exact={bit}/{N} input_sha={sha(x_cpu)},{sha(y_cpu)} golden_sha={sha(golden)}")
    return ok, bit


def main():
    results = {}
    for label, fn in [("G1_uniform", g1), ("G2_boundary", g2)]:
        x, y = fn()
        ok, bit = check(label, x, y)
        results[label] = (ok, bit)
    all_ok = all(ok for ok, _ in results.values())
    print(f"[{which}] M0B_{'PASS' if all_ok else 'FAIL'} "
          + " ".join(f"{k}:ok={v[0]},bitexact={v[1]}/{N}" for k, v in results.items()))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
