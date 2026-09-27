# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""独立故障：不是从某一条规则改一处得到的。

同时把 UB 写超，并且搬运之后直接计算、没有 sync。
只报告实际诊断，不进 M4 召回分母。
"""

from ascendc_ir import f32, gmptr, kernel, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def agent_double_fault(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 40000, stages=2)
    y_local = ubuf(f32, 40000, stages=2)
    z_local = ubuf(f32, 2048)
    mte2.copy(x[0], x_local[0])
    mte2.copy(y[0], y_local[0])
    v.add(z_local, x_local[0], y_local[0])
    mte3.copy(z_local, z[0])


SAMPLE = agent_double_fault
