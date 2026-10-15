"""L2 apply_adam_w case1：AdamW 逐元素更新链，[1024,1024]x4 f32。

attrs: lr=0.001 beta1=0.9 beta2=0.999 weight_decay=0 epsilon=1e-8 maximize=false step=1
y = var - lr * m_hat/(sqrt(v_hat)+eps)，m_hat/v_hat 为偏置校正（step=1 时 1-b^t 即 1-b）。
"""
from ascendc_ir import f32, gmptr, kernel, sync, ubuf
from ascendc_ir.pipes import mte2, mte3, v

TILE = 4096
TILES = 256


@kernel(device="ascend950pr")
def apply_adam_w_f32(var: gmptr(f32), grad: gmptr(f32), m: gmptr(f32), v_: gmptr(f32), y: gmptr(f32)):
    var_l = ubuf(f32, TILE, stages=2)
    grad_l = ubuf(f32, TILE, stages=2)
    m_l = ubuf(f32, TILE, stages=2)
    v_l = ubuf(f32, TILE, stages=2)
    m_new = ubuf(f32, TILE, stages=1)
    v_new = ubuf(f32, TILE, stages=1)
    m_hat = ubuf(f32, TILE, stages=1)
    v_hat = ubuf(f32, TILE, stages=1)
    sq = ubuf(f32, TILE, stages=1)
    den = ubuf(f32, TILE, stages=1)
    upd = ubuf(f32, TILE, stages=1)
    scaled = ubuf(f32, TILE, stages=1)
    y_l = ubuf(f32, TILE, stages=1)
    for i in range(TILES):
        mte2.copy(var[i * TILE], var_l[i % 2])
        mte2.copy(grad[i * TILE], grad_l[i % 2])
        mte2.copy(m[i * TILE], m_l[i % 2])
        mte2.copy(v_[i * TILE], v_l[i % 2])
        sync(mte2, v, on=(var_l, grad_l, m_l, v_l), stage=i)
        v.mul_scalar(m_new, m_l[i % 2], 0.9)
        v.mul_scalar(upd, grad_l[i % 2], 0.1)
        v.add(m_new, m_new, upd)
        v.mul_scalar(v_new, v_l[i % 2], 0.999)
        v.mul(scaled, grad_l[i % 2], grad_l[i % 2])
        v.mul_scalar(scaled, scaled, 0.001)
        v.add(v_new, v_new, scaled)
        v.mul_scalar(m_hat, m_new, 10.0)
        v.mul_scalar(v_hat, v_new, 1000.0)
        v.sqrt(sq, v_hat)
        v.add_scalar(den, sq, 1e-8)
        v.div(upd, m_hat, den)
        v.mul_scalar(scaled, upd, 0.001)
        v.sub(y_l, var_l[i % 2], scaled)
        sync(v, mte3, on=y_l)
        mte3.copy(y_l, y[i * TILE])
