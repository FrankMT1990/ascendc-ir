import torch

try:
    from . import _C
except ImportError as e:
    raise ImportError("Cannot import _C. Please install the cann_bench package.") from e


def add_f32_16384(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return torch.ops.cann_bench.add_f32_16384(x, y)


def leakyrelu_f32(x: torch.Tensor) -> torch.Tensor:
    return torch.ops.cann_bench.leakyrelu_f32(x)


def cast_half_to_float(x: torch.Tensor) -> torch.Tensor:
    return torch.ops.cann_bench.cast_half_to_float(x)


def reduce_sum_f32(x: torch.Tensor) -> torch.Tensor:
    return torch.ops.cann_bench.reduce_sum_f32(x)
