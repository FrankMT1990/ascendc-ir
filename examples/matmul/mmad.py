# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""单核 f16 矩阵乘。K 分成两段累加。B 按 (n, k) 存放，结果是 A @ B.T，写回 f32。"""

from ascendc_ir import f16, f32, gmptr, kernel, l0a, l0b, l0c, l1buf, sync
from ascendc_ir.pipes import fix, m, mte1, mte2

M = N = K = 32
KTILE = 16
KTILES = K // KTILE


@kernel(device="ascend950pr")
def mmad_custom(a: gmptr(f16), b: gmptr(f16), c: gmptr(f32)):
    a_l1 = l1buf(f16, M * KTILE)
    b_l1 = l1buf(f16, N * KTILE)
    a_l0 = l0a(f16, M * KTILE)
    b_l0 = l0b(f16, N * KTILE)
    c_l0 = l0c(f32, M * N)
    for kt in range(KTILES):
        mte2.nd2nz(a[kt * KTILE], a_l1, M, KTILE, row_stride=K)
        mte2.nd2nz(b[kt * KTILE], b_l1, N, KTILE, row_stride=K)
        sync(mte2, mte1, on=(a_l1, b_l1), stage=kt)
        mte1.l12l0a(a_l1, a_l0, M, KTILE)
        mte1.l12l0b(b_l1, b_l0, N, KTILE)
        sync(mte1, m, on=(a_l0, b_l0), stage=kt)
        m.mmad(c_l0, a_l0, b_l0, M, KTILE, N, init=(kt == 0))
    sync(m, fix, on=c_l0)
    fix.l0c2gm(c_l0, c[0], M, N)
