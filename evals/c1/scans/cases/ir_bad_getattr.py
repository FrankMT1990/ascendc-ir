from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

PART = "ad"


@kernel(device="ascend950pr")
def bad_getattr(x: gmptr(f32), z: gmptr(f32)):
    x_local = ubuf(f32, 2048, stages=1)
    z_local = ubuf(f32, 2048, stages=1)
    mte2.copy(x[0], x_local)
    sync(mte2, v, on=(x_local,))
    op = getattr(v, PART + "d")
    op(z_local, x_local, x_local)
    sync(v, mte3, on=z_local)
    mte3.copy(z_local, z[0])
