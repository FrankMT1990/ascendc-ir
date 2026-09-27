# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""边界合法：UB 刚好用满 253952 字节，不得误拒。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3


@kernel(device="ascend950pr")
def boundary_ub(x: gmptr(f32), z: gmptr(f32)):
    # 63488 * 4 = 253952，等于设备表 ub_usable_bytes。
    local = ubuf(f32, 63488)
    mte2.copy(x[0], local[0])
    sync(mte2, mte3, on=local)
    mte3.copy(local[0], z[0])


SAMPLE = boundary_ub
