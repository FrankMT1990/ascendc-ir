# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""合法样本：单 tile LeakyReLU（改写自官方 fused_compute 样例）。"""

from ascendc_ir import f16, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def leakyrelu_legal(x: gmptr(f16), y: gmptr(f16)):
    x_local = ubuf(f16, 512)
    y_local = ubuf(f16, 512)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.leakyrelu(y_local[0], x_local[0], 0.01)
    sync(v, mte3, on=y_local)
    mte3.copy(y_local[0], y[0])


SAMPLE = leakyrelu_legal
