#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M0 冒烟：装好的 cann_bench wheel 跑一次冻结输入，检查数值。不计分。"""
import sys
import torch
import torch_npu
import cann_bench

which = sys.argv[1] if len(sys.argv) > 1 else "unknown"

torch.manual_seed(0)
x_cpu = torch.rand(16384) * 4 - 2
y_cpu = torch.rand(16384) * 4 - 2
x = x_cpu.npu()
y = y_cpu.npu()
z = cann_bench.add(x, y)
torch.npu.synchronize()
z_cpu = z.cpu()

golden = torch.add(x_cpu, y_cpu)
diff = (z_cpu - golden).abs()
tol = 1e-6 + 1e-6 * golden.abs()
ok = bool((diff <= tol).all())
bitexact = int((z_cpu.view(torch.int32) == golden.view(torch.int32)).sum().item())
print(f"[smoke:{which}] dtype={z_cpu.dtype} shape={tuple(z_cpu.shape)}")
print(f"[smoke:{which}] nan={bool(torch.isnan(z_cpu).any())} max_abs_diff={diff.max().item():.3e}")
print(f"[smoke:{which}] tolerance_ok={ok} bit_exact={bitexact}/16384")
print(f"[smoke:{which}] sample z={z_cpu[:3].tolist()} golden={golden[:3].tolist()}")
assert ok, "smoke FAILED tolerance"
print(f"[smoke:{which}] SMOKE_OK")
