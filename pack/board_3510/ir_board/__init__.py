import torch

try:
    from . import _C
except ImportError as e:
    raise ImportError("Cannot import _C. Install the ir_board package first.") from e

def op_add(*args):
    return torch.ops.ir_board.op_add(*args)

def op_sub(*args):
    return torch.ops.ir_board.op_sub(*args)

def op_mul(*args):
    return torch.ops.ir_board.op_mul(*args)

def op_div(*args):
    return torch.ops.ir_board.op_div(*args)

def op_max(*args):
    return torch.ops.ir_board.op_max(*args)

def op_min(*args):
    return torch.ops.ir_board.op_min(*args)

def op_and(*args):
    return torch.ops.ir_board.op_and(*args)

def op_or(*args):
    return torch.ops.ir_board.op_or(*args)

def op_prelu(*args):
    return torch.ops.ir_board.op_prelu(*args)

def op_abs(*args):
    return torch.ops.ir_board.op_abs(*args)

def op_ceil(*args):
    return torch.ops.ir_board.op_ceil(*args)

def op_exp(*args):
    return torch.ops.ir_board.op_exp(*args)

def op_floor(*args):
    return torch.ops.ir_board.op_floor(*args)

def op_ln(*args):
    return torch.ops.ir_board.op_ln(*args)

def op_log(*args):
    return torch.ops.ir_board.op_log(*args)

def op_neg(*args):
    return torch.ops.ir_board.op_neg(*args)

def op_not(*args):
    return torch.ops.ir_board.op_not(*args)

def op_relu(*args):
    return torch.ops.ir_board.op_relu(*args)

def op_rint(*args):
    return torch.ops.ir_board.op_rint(*args)

def op_round(*args):
    return torch.ops.ir_board.op_round(*args)

def op_sqrt(*args):
    return torch.ops.ir_board.op_sqrt(*args)

def op_trunc(*args):
    return torch.ops.ir_board.op_trunc(*args)

def op_add_scalar(*args):
    return torch.ops.ir_board.op_add_scalar(*args)

def op_max_scalar(*args):
    return torch.ops.ir_board.op_max_scalar(*args)

def op_min_scalar(*args):
    return torch.ops.ir_board.op_min_scalar(*args)

def op_mul_scalar(*args):
    return torch.ops.ir_board.op_mul_scalar(*args)

def op_leakyrelu(*args):
    return torch.ops.ir_board.op_leakyrelu(*args)

def op_select(*args):
    return torch.ops.ir_board.op_select(*args)

def op_select_gt(*args):
    return torch.ops.ir_board.op_select_gt(*args)

def op_select_lt(*args):
    return torch.ops.ir_board.op_select_lt(*args)

def op_select_ne(*args):
    return torch.ops.ir_board.op_select_ne(*args)

def op_select_eq(*args):
    return torch.ops.ir_board.op_select_eq(*args)

def op_select_ge(*args):
    return torch.ops.ir_board.op_select_ge(*args)

def op_select_le(*args):
    return torch.ops.ir_board.op_select_le(*args)

def op_select_gt_scalar(*args):
    return torch.ops.ir_board.op_select_gt_scalar(*args)

def op_select_lt_scalar(*args):
    return torch.ops.ir_board.op_select_lt_scalar(*args)

def op_select_ne_scalar(*args):
    return torch.ops.ir_board.op_select_ne_scalar(*args)

def op_select_eq_scalar(*args):
    return torch.ops.ir_board.op_select_eq_scalar(*args)

def op_select_ge_scalar(*args):
    return torch.ops.ir_board.op_select_ge_scalar(*args)

def op_select_le_scalar(*args):
    return torch.ops.ir_board.op_select_le_scalar(*args)

def op_duplicate(*args):
    return torch.ops.ir_board.op_duplicate(*args)

def op_arange(*args):
    return torch.ops.ir_board.op_arange(*args)

def op_xor(*args):
    return torch.ops.ir_board.op_xor(*args)

def op_shiftleft(*args):
    return torch.ops.ir_board.op_shiftleft(*args)

def op_shiftright(*args):
    return torch.ops.ir_board.op_shiftright(*args)

def op_shiftleft_scalar(*args):
    return torch.ops.ir_board.op_shiftleft_scalar(*args)

def op_shiftright_scalar(*args):
    return torch.ops.ir_board.op_shiftright_scalar(*args)

def op_cast(*args):
    return torch.ops.ir_board.op_cast(*args)

def op_repeat_reduce_sum(*args):
    return torch.ops.ir_board.op_repeat_reduce_sum(*args)

def op_mmad(*args):
    return torch.ops.ir_board.op_mmad(*args)
