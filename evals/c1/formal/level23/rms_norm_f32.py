"""L2 rms_norm case2：y = x/sqrt(mean(x^2)+eps) * gamma，[32,128,1024] f32，行=1024=tile。"""
from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 1024
TILES = 32 * 128
EPS = 1e-6


@kernel(device="ascend950pr")
def rms_norm_f32(x: gmptr(f32), gamma: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, TILE, stages=2)
    gamma_local = ubuf(f32, TILE, stages=1)
    sq = ubuf(f32, TILE, stages=1)
    sum_vf = ubuf(f32, 64)
    inv_n = ubuf(f32, 64)
    z_local = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(x[i * TILE], x_local[i % 2])
        mte2.copy(gamma[0], gamma_local)
        sync(mte2, v, on=(x_local, gamma_local), stage=i)
        v.mul(sq, x_local[i % 2], x_local[i % 2])
        v.repeat_reduce_sum(sum_vf, sq)
        v.mul_scalar(inv_n, sum_vf, 1.0 / (TILE * 1.0))
        v.sqrt(inv_n, inv_n)
        v.add_scalar(inv_n, inv_n, EPS)
        v.div(z_local, x_local[i % 2], inv_n)
        v.mul(z_local, z_local, gamma_local)
        sync(v, mte3, on=z_local)
        mte3.copy(z_local, z[i * TILE])
