# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""边界合法：单 stage 刚好 32 字节，不得误拒。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def boundary_align(x: gmptr(f32), z: gmptr(f32)):
    local = ubuf(f32, 8)
    out = ubuf(f32, 8)
    mte2.copy(x[0], local[0])
    sync(mte2, v, on=local)
    v.add(out, local, local)
    sync(v, mte3, on=out)
    mte3.copy(out, z[0])


SAMPLE = boundary_align
