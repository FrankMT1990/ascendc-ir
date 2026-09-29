"""One-shot numeric check for add, leakyrelu, cast, and reduce_sum."""

import torch
import torch_npu
from cann_bench import add_f32_16384, cast_half_to_float, leakyrelu_f32, reduce_sum_f32


def report(name, a, golden, tol_abs=1e-6, tol_rel=1e-6):
    diff = (a - golden).abs()
    tol = tol_abs + tol_rel * golden.abs()
    print(
        name,
        "dtype", str(a.dtype),
        "numel", int(a.numel()),
        "nan", int(torch.isnan(a).sum()),
        "max_abs", float(diff.max()) if a.numel() else 0.0,
        "tol_ok", bool((diff <= tol).all()) if a.numel() else False,
        "bit", int((a.view(torch.int32) == golden.view(torch.int32)).sum()) if a.dtype == torch.float32 else -1,
        "/", int(golden.numel()),
    )


def main():
    torch.manual_seed(0)
    x = torch.rand(16384) * 4 - 2
    y = torch.rand(16384) * 4 - 2
    z = add_f32_16384(x.npu(), y.npu())
    torch.npu.synchronize()
    report("add_G1", z.cpu(), torch.add(x, y))

    got = leakyrelu_f32(x.npu())
    torch.npu.synchronize()
    golden = torch.where(x > 0, x, 0.1 * x)
    report("leakyrelu_G1", got.cpu(), golden)

    hx = (torch.rand(1024) * 4 - 2).half()
    got = cast_half_to_float(hx.npu())
    torch.npu.synchronize()
    report("cast_G1", got.cpu(), hx.float())

    ones = torch.ones(256)
    lanes = reduce_sum_f32(ones.npu())
    torch.npu.synchronize()
    lanes = lanes.cpu()
    print(
        "reduce_ones",
        "lane_sum", float(lanes.sum()),
        "golden", float(ones.sum()),
        "abs_err", float((lanes.sum() - ones.sum()).abs()),
        "nan", int(torch.isnan(lanes).sum()),
    )

    small = torch.rand(256) * 0.01
    lanes = reduce_sum_f32(small.npu())
    torch.npu.synchronize()
    lanes = lanes.cpu()
    err = (lanes.sum() - small.sum()).abs()
    print(
        "reduce_small",
        "lane_sum", float(lanes.sum()),
        "golden", float(small.sum()),
        "abs_err", float(err),
        "nan", int(torch.isnan(lanes).sum()),
    )


if __name__ == "__main__":
    main()
