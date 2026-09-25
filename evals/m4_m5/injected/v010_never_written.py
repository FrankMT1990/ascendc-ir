# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""注入 V010：读取从未写入过的槽位。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def v010_never_written(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.add(z_local, x_local, z_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


SAMPLE = v010_never_written
