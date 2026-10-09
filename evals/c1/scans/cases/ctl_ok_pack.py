import torch
import torch_npu
from torch_npu.csrc.core.npu import NPUStream


def run_vector(x, z):
    stream = NPUStream.current()
    launch(x, z, stream)
    return z
