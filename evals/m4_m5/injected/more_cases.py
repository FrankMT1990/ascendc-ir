# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.

"""每条已测规则再补两个单点注入，使分母至少为 3。每个函数只改一处。"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v


@kernel(device="ascend950pr")
def v001_tile_1024(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    tile = 1024
    x_local = ubuf(f32, tile, stages=2)
    y_local = ubuf(f32, tile, stages=2)
    z_local = ubuf(f32, tile, stages=1)
    for i in range(4):
        mte3.copy(x[i * 1024], x_local[i % 2])
        mte3.copy(y[i * 1024], y_local[i % 2])
        sync(mte3, v, on=(x_local, y_local), stage=i)
        v.add(z_local, x_local[i % 2], y_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * 1024])


@kernel(device="ascend950pr")
def v001_tile_512(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    tile = 512
    x_local = ubuf(f32, tile, stages=2)
    y_local = ubuf(f32, tile, stages=2)
    z_local = ubuf(f32, tile, stages=1)
    for i in range(4):
        mte3.copy(x[i * 512], x_local[i % 2])
        mte3.copy(y[i * 512], y_local[i % 2])
        sync(mte3, v, on=(x_local, y_local), stage=i)
        v.add(z_local, x_local[i % 2], y_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * 512])


@kernel(device="ascend950pr")
def v002_elems_50000(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 50000, stages=2)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.add(z_local, x_local[0], x_local[0])
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v002_elems_45000(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 45000, stages=2)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.add(z_local, x_local[0], x_local[0])
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v003_spare(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    spare = ubuf(f32, 32)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    mte2.copy(x[0], spare[0])
    sync(mte2, v, on=(x_local, spare))
    v.add(z_local, x_local, x_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v003_extra(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    extra = ubuf(f32, 128)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    mte2.copy(x[0], extra[0])
    sync(mte2, v, on=(extra, x_local))
    v.add(z_local, x_local, x_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v004_flip_1024(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    tile = 1024
    x_local = ubuf(f32, tile, stages=2)
    y_local = ubuf(f32, tile, stages=2)
    z_local = ubuf(f32, tile, stages=1)
    for i in range(4):
        mte2.copy(x[i * 1024], x_local[i % 2])
        mte2.copy(y[i * 1024], y_local[i % 2])
        sync(mte2, v, on=(x_local, y_local), stage=i)
        sync(v, mte2, on=(x_local, y_local), stage=i)  # flip-1024
        v.add(z_local, x_local[i % 2], y_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * 1024])


@kernel(device="ascend950pr")
def v004_flip_512(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    tile = 512
    x_local = ubuf(f32, tile, stages=2)
    y_local = ubuf(f32, tile, stages=2)
    z_local = ubuf(f32, tile, stages=1)
    for i in range(4):
        mte2.copy(x[i * 512], x_local[i % 2])
        mte2.copy(y[i * 512], y_local[i % 2])
        sync(mte2, v, on=(x_local, y_local), stage=i)
        sync(v, mte2, on=(x_local, y_local), stage=i)  # flip-512
        v.add(z_local, x_local[i % 2], y_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * 512])


@kernel(device="ascend950pr")
def v005_ten(x: gmptr(f32), z: gmptr(f32)):
    bufs = []
    for _ in range(10):
        bufs.append(ubuf(f32, 8))
    z_local = ubuf(f32, 8)
    for b in bufs:
        mte2.copy(x[0], b[0])
    for b in bufs:
        sync(mte2, v, on=b)  # ten
    for b in bufs:
        v.add(b, b, b)
    v.add(z_local, bufs[0], bufs[1])
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v005_twelve(x: gmptr(f32), z: gmptr(f32)):
    bufs = []
    for _ in range(12):
        bufs.append(ubuf(f32, 8))
    z_local = ubuf(f32, 8)
    for b in bufs:
        mte2.copy(x[0], b[0])
    for b in bufs:
        sync(mte2, v, on=b)  # twelve
    for b in bufs:
        v.add(b, b, b)
    v.add(z_local, bufs[0], bufs[1])
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v006_gm_x(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64, stages=2)
    y_local = ubuf(f32, 64, stages=2)
    z_local = ubuf(f32, 64)
    for i in range(2):
        mte2.copy(x[i * 64], x_local[i % 2])
        mte2.copy(y[i * 64], y_local[i % 2])
        sync(mte2, v, on=(x_local, y_local), stage=i)
        v.add(z_local, x_local[i % 2], y_local[i % 2])
        v.add(z_local, x[i * 64], y_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * 64])


@kernel(device="ascend950pr")
def v006_gm_z(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    y_local = ubuf(f32, 64)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    mte2.copy(y[0], y_local[0])
    sync(mte2, v, on=(x_local, y_local))
    v.add(z_local, x_local, y_local)
    v.add(z[0], x_local, y_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[64])


@kernel(device="ascend950pr")
def v007_elems_1(x: gmptr(f32), y: gmptr(f32)):
    x_local = ubuf(f32, 1)
    y_local = ubuf(f32, 8)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.repeat_reduce_sum(y_local[0], x_local[0])
    sync(v, mte3, on=y_local)
    mte3.copy(y_local[0], y[0])


@kernel(device="ascend950pr")
def v007_elems_7(x: gmptr(f32), y: gmptr(f32)):
    x_local = ubuf(f32, 7)
    y_local = ubuf(f32, 8)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.repeat_reduce_sum(y_local[0], x_local[0])
    sync(v, mte3, on=y_local)
    mte3.copy(y_local[0], y[0])


@kernel(device="ascend950pr")
def v009_drop_mte3(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    y_local = ubuf(f32, 64)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    mte2.copy(y[0], y_local[0])
    sync(mte2, v, on=(x_local, y_local))
    v.add(z_local, x_local, y_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v009_drop_one_input(x: gmptr(f32), y: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    y_local = ubuf(f32, 64)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    mte2.copy(y[0], y_local[0])
    sync(mte2, v, on=x_local)
    v.add(z_local, x_local, y_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v010_read_w(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    w_local = ubuf(f32, 64)
    z_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.add(z_local, x_local, w_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])


@kernel(device="ascend950pr")
def v010_read_dst(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 64)
    out_local = ubuf(f32, 64)
    mte2.copy(x[0], x_local[0])
    sync(mte2, v, on=x_local)
    v.add(out_local, x_local, out_local)
    sync(v, mte3, on=out_local)
    mte3.copy(out_local, z[0])
