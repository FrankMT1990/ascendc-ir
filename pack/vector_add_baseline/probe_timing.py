#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vector_add T_baseline / T_HW 计时探针。

复刻本机 CANNBench/harness 既有纪律（M0 manifest v1.2 冻结参数）：
- 计时窗口前一次：cann_bench_warmup（MatMul 10240×10240 f16 ×2）升频 + cann_bench_cache_clean（ReduceMax 96×1024×1024 f16）清 L2
- 每个测量 step 前：cann_bench_cache_clean + sync（harness _clear_cache）
- profiler schedule wait=0 / warmup=3 / active=20；判分只读原始 kernel_details.csv；统计量=中位
用法：PROBE_OP=add|floor|aclnn|m0 PROBE_OUT=<dir> python3 probe_timing.py
"""
import csv
import glob
import hashlib
import os
import shutil
import statistics
import sys
from collections import Counter

import torch
import torch_npu
from torch_npu.profiler import ProfilerActivity, profile, schedule, tensorboard_trace_handler

OP = os.environ.get("PROBE_OP", "add")
OUT = os.environ.get("PROBE_OUT", "/tmp/probe_out")

sys.path.insert(0, "/home/w00964611/cann-bench/src")
from cann_bench_utils import cann_bench_warmup, cann_bench_cache_clean

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)

print("PROBE_OP:", OP)
print("device:", torch.npu.get_device_name(0))
print("ASCEND_TOOLKIT_HOME:", os.environ.get("ASCEND_TOOLKIT_HOME"))

import cann_bench
so_path = os.path.join(os.path.dirname(cann_bench.__file__), "_C.abi3.so")
print("loaded _C.abi3.so sha256:", hashlib.sha256(open(so_path, "rb").read()).hexdigest()[:16])

torch.manual_seed(0)
x_cpu = torch.rand(16384) * 4 - 2
y_cpu = torch.rand(16384) * 4 - 2
x, y = x_cpu.npu(), y_cpu.npu()

mm1 = torch.rand((10240, 10240), dtype=torch.float16).npu()
mm2 = torch.rand((10240, 10240), dtype=torch.float16).npu()
reduce_input = torch.rand((96, 1024, 1024), dtype=torch.float16).npu()

# 计时窗口前一次：升频 + 清 cache
cann_bench_warmup(mm1, mm2)
torch.npu.synchronize(mm1.device)
cann_bench_cache_clean(reduce_input)
torch.npu.synchronize(reduce_input.device)

if OP == "aclnn":
    def run():
        return torch.add(x, y)
elif OP == "floor":
    def run():
        return cann_bench.add_or_floor(x, y)
elif OP == "m0":
    def run():
        return cann_bench.add(x, y)
else:
    def run():
        return cann_bench.add_f32_16384(x, y)

# 数值确认（一次）：m0 模式下同时打印 add/or 两种 golden，自识别装载的是哪个内核
z = run()
torch.npu.synchronize()
zc = z.cpu()
add_golden = torch.add(x_cpu, y_cpu)
or_golden = (x_cpu.view(torch.int32) | y_cpu.view(torch.int32)).view(torch.float32)
print("vs_add_golden bit_exact:", int((zc.view(torch.int32) == add_golden.view(torch.int32)).sum()), "/16384")
print("vs_or_golden  bit_exact:", int((zc.view(torch.int32) == or_golden.view(torch.int32)).sum()), "/16384")

# 计时窗口：23 步 = 3 warmup（丢弃）+ 20 active
with profile(
    activities=[ProfilerActivity.NPU],
    schedule=schedule(wait=0, warmup=3, active=20, repeat=1),
    on_trace_ready=tensorboard_trace_handler(OUT),
    with_stack=False,
    record_shapes=False,
    profile_memory=False,
) as prof:
    for _ in range(23):
        cann_bench_cache_clean(reduce_input)
        torch.npu.synchronize(reduce_input.device)
        run()
        torch.npu.synchronize()
        prof.step()

kd = sorted(glob.glob(os.path.join(OUT, "**", "kernel_details.csv"), recursive=True))
if not kd:
    print("NO kernel_details.csv")
    sys.exit(3)
print("csv:", kd[-1])

with open(kd[-1], encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

names = Counter((r.get("Name") or "").strip() for r in rows)
print("kernel rows:", dict(names))

def is_clean(r):
    n = (r.get("Name") or "")
    return ("CannBenchCacheClean" in n) or ("CannBenchWarmup" in n)

target = []
for r in rows:
    if is_clean(r):
        continue
    d = (r.get("Duration(us)") or "").strip()
    if d:
        target.append(float(d))

print("target_rows:", len(target))
print("per_step_us:", [round(t, 3) for t in target])
print("MEDIAN_us:", round(statistics.median(target), 3) if target else None)
for r in rows[:4]:
    print("sample:", {k: r.get(k) for k in ("Name", "Type", "Duration(us)", "Block Num")})
