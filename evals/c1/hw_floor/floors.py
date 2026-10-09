"""C1 第 2 步 T_HW 下界核：每个清单任务的 or-floor 形态。

同一 shape、单核、流水搬运 + 最少向量指令（or）。计算被搬运掩盖，
得到的 kernel-only 中位时延作为该任务的硬件时延下界 T_HW。
"""

from ascendc_ir import f32, gmptr, kernel, sync, ubuf, u8
from ascendc_ir.pipes import mte2, mte3, v

TILE = 2048


@kernel(device="ascend950pr")
def floor_exp(x: gmptr(f32), z: gmptr(f32)):
    """exp_f32 [2048,2048]：读 16MB 写 16MB。"""
    TILES = 2048
    x_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local,), stage=i)
        v.compute("or", z_local, (x_local[i % 2], x_local[i % 2]))
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])


@kernel(device="ascend950pr")
def floor_sigmoid(x: gmptr(f32), z: gmptr(f32)):
    """sigmoid_f32 [2048,2048]：读 16MB 写 16MB。"""
    TILES = 2048
    x_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local,), stage=i)
        v.compute("or", z_local, (x_local[i % 2], x_local[i % 2]))
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])


@kernel(device="ascend950pr")
def floor_gelu(x: gmptr(f32), z: gmptr(f32)):
    """gelu_f32 [8192,8192]：读 268MB 写 268MB。"""
    TILES = 32768
    x_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local,), stage=i)
        v.compute("or", z_local, (x_local[i % 2], x_local[i % 2]))
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])


@kernel(device="ascend950pr")
def floor_mish(x: gmptr(f32), z: gmptr(f32)):
    """mish_f32 [2048,2048]：读 16MB 写 16MB。"""
    TILES = 2048
    x_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        sync(mte2, v, on=(x_local,), stage=i)
        v.compute("or", z_local, (x_local[i % 2], x_local[i % 2]))
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])


@kernel(device="ascend950pr")
def floor_masked_scale(x: gmptr(f32), mask: gmptr(u8), z: gmptr(f32)):
    """masked_scale_f32 [2048,2048] 的真实 select 数据流。

    主流每块 2048 个 f32；位打包掩码每块 1024 个 u8（= f32 个数 x 4 / 8）。
    select(x, x, mask) 数值上恒等于 x，只取其数据流：读 x 流、读掩码流、
    写出一条流，与 scale=1.0 的真实核 select(x*scale, 0, mask) 流量一致。
    """
    TILES = 2048
    MASK_TILE = TILE * 4 // 8
    x_local = ubuf(f32, TILE, stages=2)
    mask_local = ubuf(u8, MASK_TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        mte2.copy(mask[i * MASK_TILE], mask_local[i % 2])
        sync(mte2, v, on=(x_local, mask_local), stage=i)
        v.select(z_local, x_local[i % 2], x_local[i % 2], mask_local[i % 2])
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])


@kernel(device="ascend950pr")
def floor_swi_glu(x0: gmptr(f32), x1: gmptr(f32), z: gmptr(f32)):
    """swi_glu_f32 [2048,4096] 分半：读 x0 16MB + x1 16MB，写 16MB。"""
    TILES = 2048
    x0_local = ubuf(f32, TILE, stages=2)
    x1_local = ubuf(f32, TILE, stages=2)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x0[i * TILE], x0_local[i % 2])
        mte2.copy(x1[i * TILE], x1_local[i % 2])
        sync(mte2, v, on=(x0_local, x1_local), stage=i)
        v.compute("or", z_local, (x0_local[i % 2], x1_local[i % 2]))
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])


@kernel(device="ascend950pr")
def floor_foreach_addcdiv(x1: gmptr(f32), x2: gmptr(f32), x3: gmptr(f32), z: gmptr(f32)):
    """foreach_addcdiv_f32：x1/x2/x3 各 [2,1024,1024]（连续视角），输出 z [2,1024,1024]。

    每块读三路 2048 f32、写一路；两条 or 只为让三路输入都被计算管线消费，
    计算仍在搬运掩盖下。布局为连续父张量视角，T_baseline 侧是独立 tensor 列表，
    搬运总量一致（3 x 8MB 读 + 8MB 写）。
    """
    TILES = 1024
    x1_local = ubuf(f32, TILE, stages=2)
    x2_local = ubuf(f32, TILE, stages=2)
    x3_local = ubuf(f32, TILE, stages=2)
    t_local = ubuf(f32, TILE, stages=1)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x1[i * TILE], x1_local[i % 2])
        mte2.copy(x2[i * TILE], x2_local[i % 2])
        mte2.copy(x3[i * TILE], x3_local[i % 2])
        sync(mte2, v, on=(x1_local, x2_local, x3_local), stage=i)
        v.compute("or", t_local, (x2_local[i % 2], x3_local[i % 2]))
        v.compute("or", z_local, (x1_local[i % 2], t_local))
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])
