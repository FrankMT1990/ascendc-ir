# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""注入 V005：同一 PIPE 对上 9 条未决 sync，超过每对 event_ids=8。基线：legal/reduce_legal.py 的单 tile 形态。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def v005_event_pressure(x: gmptr(f32), z: gmptr(f32)):
    bufs = []
    for _ in range(9):
        bufs.append(ubuf(f32, 8))
    z_local = ubuf(f32, 8)
    for b in bufs:
        mte2.copy(x[0], b[0])
    for b in bufs:
        sync(mte2, v, on=b)
    for b in bufs:
        v.add(b, b, b)
    v.add(z_local, bufs[0], bufs[1])
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


SAMPLE = v005_event_pressure
