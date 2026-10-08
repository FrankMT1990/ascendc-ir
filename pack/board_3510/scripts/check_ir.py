"""Batch numeric check for the IR kernels in this pack. Runs on the 950."""

import json
import sys
from pathlib import Path

import torch
import torch_npu

import ir_board


ROOT = Path(__file__).resolve().parents[1]
N = 64
TOL_OPS = {"div", "exp", "ln", "log", "sqrt", "leakyrelu"}


def f32_inputs():
    i = torch.arange(N)
    x = (i % 7).to(torch.float32) - 3.0 + 0.125
    y = (i % 5).to(torch.float32) + 1.0
    y = y.clone()
    y[0] = x[0]
    return x, y


def positive(x):
    return x.abs() + 0.5


def i32_inputs():
    x = torch.arange(N, dtype=torch.int32) + 1
    y = (torch.arange(N, dtype=torch.int32) % 5) + 1
    return x, y


def select_mask():
    mask = torch.zeros(N // 2, dtype=torch.uint8)
    for i in range(N):
        if i % 2 == 0:
            mask[i // 2] |= 1 << ((i % 2) * 4)
    return mask


def bits_equal(got, golden):
    if got.dtype == torch.float32:
        return int((got.view(torch.int32) == golden.view(torch.int32)).sum())
    return int((got == golden).sum())


def report(name, got, golden, tol):
    got = got.detach().cpu().contiguous()
    golden = golden.detach().cpu().contiguous()
    diff = (got - golden).abs() if got.dtype.is_floating_point else (got != golden).to(torch.float32)
    max_abs = float(diff.max()) if diff.numel() else 0.0
    matched = bits_equal(got, golden)
    if tol:
        limit = 1e-4 + 1e-4 * golden.abs()
        ok = bool((diff <= limit).all())
    else:
        ok = matched == int(golden.numel())
    print(
        name,
        "ok", ok,
        "bit", matched, "/", int(golden.numel()),
        "max_abs", max_abs,
        "nan", int(torch.isnan(got).sum()) if got.dtype.is_floating_point else 0,
    )
    return ok


def golden_bin(op, x, y):
    table = {
        "add": x + y,
        "sub": x - y,
        "mul": x * y,
        "div": x / y,
        "max": torch.maximum(x, y),
        "min": torch.minimum(x, y),
        "and": (x.view(torch.int32) & y.view(torch.int32)).view(torch.float32),
        "or": (x.view(torch.int32) | y.view(torch.int32)).view(torch.float32),
        "prelu": torch.where(x > 0, x, x * y),
        "select_gt": torch.where(x > y, x, y),
        "select_lt": torch.where(x < y, x, y),
        "select_ne": torch.where(x != y, x, y),
        "select_eq": torch.where(x == y, x, y),
        "select_ge": torch.where(x >= y, x, y),
        "select_le": torch.where(x <= y, x, y),
        "select_gt_scalar": torch.where(x > 1, x, y),
        "select_lt_scalar": torch.where(x < 1, x, y),
        "select_ne_scalar": torch.where(x != 1, x, y),
        "select_eq_scalar": torch.where(x == 1, x, y),
        "select_ge_scalar": torch.where(x >= 1, x, y),
        "select_le_scalar": torch.where(x <= 1, x, y),
    }
    return table[op]


def golden_unary(op, x):
    table = {
        "abs": x.abs(),
        "ceil": torch.ceil(x),
        "exp": torch.exp(x),
        "floor": torch.floor(x),
        "ln": torch.log(x),
        "log": torch.log(x),
        "neg": -x,
        "not": (~x.view(torch.int32)).view(torch.float32),
        "relu": torch.relu(x),
        "rint": torch.round(x),
        "round": torch.round(x),
        "sqrt": torch.sqrt(x),
        "trunc": torch.trunc(x),
        "add_scalar": x + 1.5,
        "max_scalar": torch.maximum(x, torch.tensor(1.0)),
        "min_scalar": torch.minimum(x, torch.tensor(1.0)),
        "mul_scalar": x * 2,
        "leakyrelu": torch.where(x > 0, x, 0.1 * x),
    }
    return table[op]


def main():
    torch.npu.set_device(0)
    manifest = json.loads((ROOT / "ops.json").read_text(encoding="utf-8"))
    x, y = f32_inputs()
    xp = positive(x)
    xi, yi = i32_inputs()
    mask = select_mask()
    failed = []
    for item in manifest:
        name = item["name"]
        op = item["op"]
        kind = item["kind"]
        fn = getattr(ir_board, name)
        try:
            if kind == "bin":
                src = xp if op in {"div"} else x
                got = fn(src.npu(), y.npu())
                torch.npu.synchronize()
                golden = golden_bin(op, src, y)
            elif kind == "unary":
                src = xp if op in {"ln", "log", "sqrt"} else x
                got = fn(src.npu())
                torch.npu.synchronize()
                golden = golden_unary(op, src)
            elif kind == "select":
                got = fn(x.npu(), y.npu(), mask.npu())
                torch.npu.synchronize()
                golden = torch.where(torch.arange(N) % 2 == 0, x, y)
            elif kind == "i32_bin":
                got = fn(xi.npu(), yi.npu())
                torch.npu.synchronize()
                golden = {"xor": xi ^ yi, "shiftleft": xi << yi, "shiftright": xi >> yi}[op]
            elif kind == "i32_unary":
                got = fn(xi.npu())
                torch.npu.synchronize()
                golden = {"shiftleft_scalar": xi << 3, "shiftright_scalar": xi >> 3}[op]
            elif kind == "fill":
                got = fn(x.npu())
                torch.npu.synchronize()
                golden = {"duplicate": torch.full((N,), 3.0), "arange": torch.arange(N).to(torch.float32)}[op]
            elif kind == "cast":
                h = ((torch.arange(N) % 7) - 3).to(torch.float16)
                got = fn(h.npu())
                torch.npu.synchronize()
                golden = h.float()
            elif kind == "reduce":
                ones = torch.ones(N)
                got = fn(ones.npu())
                torch.npu.synchronize()
                lanes = got.detach().cpu()
                err = float((lanes.sum() - ones.sum()).abs())
                ok = err == 0.0 and int(torch.isnan(lanes).sum()) == 0
                print(name, "ok", ok, "lane_sum", float(lanes.sum()), "golden", float(ones.sum()), "abs_err", err)
                if not ok:
                    failed.append(name)
                continue
            elif kind == "mmad":
                a = (torch.arange(1024).reshape(32, 32) % 3).to(torch.float16)
                b = ((torch.arange(1024) * 2).reshape(32, 32) % 3).to(torch.float16)
                got = fn(a.npu(), b.npu())
                torch.npu.synchronize()
                golden = a.float().matmul(b.float().transpose(0, 1))
            else:
                raise RuntimeError(f"unknown kind {kind}")
            if not report(name, got, golden, op in TOL_OPS):
                failed.append(name)
        except Exception as exc:
            print(name, "EXC", type(exc).__name__, exc)
            failed.append(name)
    print("failed", len(failed), "of", len(manifest))
    if failed:
        print(" ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
