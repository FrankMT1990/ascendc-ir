# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""注入 V007：buffer 单 stage 字节数不满足 32B 对齐。基线：legal/reduce_legal.py。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def v007_misaligned(x: gmptr(f32), y: gmptr(f32)):
    x_local = ubuf(f32, 100)
    y_local = ubuf(f32, 8)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.repeat_reduce_sum(y_local[0], x_local[0])
    sync(v, mte3, on=y_local)
    mte3.copy(y_local[0], y[0])


SAMPLE = v007_misaligned
