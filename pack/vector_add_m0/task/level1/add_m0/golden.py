#!/usr/bin/python3
# coding=utf-8

# ----------------------------------------------------------------------------------------------------------
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This file is part of the ascendc-ir M0 measurement pack (see docs/evaluation/metrics.md).
# ----------------------------------------------------------------------------------------------------------

import torch

"""
Add算子Torch Golden参考实现（ascendc-ir M0 测量任务）

逐元素加法运算，冻结 shape 一维 16384 个 float32。
公式: y = x1 + x2
"""
def add(
    x: torch.Tensor, y: torch.Tensor
) -> torch.Tensor:
    """
    逐元素加法运算

    公式: z = x + y

    Args:
        x: 第1个输入张量
        y: 第2个输入张量（与x同shape）

    Returns:
        输出张量，逐元素加法结果
    """
    return torch.add(x, y)
