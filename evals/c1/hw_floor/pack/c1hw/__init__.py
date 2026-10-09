import torch

try:
    from . import _C
except ImportError as e:
    raise ImportError("Cannot import _C. Install the c1hw package first.") from e

__all__ = ["floor_exp", "floor_sigmoid", "floor_gelu", "floor_mish",
           "floor_masked_scale", "floor_swi_glu", "floor_foreach_addcdiv"]


def floor_exp(x):
    return torch.ops.c1hw.floor_exp(x)


def floor_sigmoid(x):
    return torch.ops.c1hw.floor_sigmoid(x)


def floor_gelu(x):
    return torch.ops.c1hw.floor_gelu(x)


def floor_mish(x):
    return torch.ops.c1hw.floor_mish(x)


def floor_masked_scale(x, mask):
    return torch.ops.c1hw.floor_masked_scale(x, mask)


def floor_swi_glu(x):
    return torch.ops.c1hw.floor_swi_glu(x)


def floor_foreach_addcdiv(x1, x2, x3):
    return torch.ops.c1hw.floor_foreach_addcdiv(x1, x2, x3)
