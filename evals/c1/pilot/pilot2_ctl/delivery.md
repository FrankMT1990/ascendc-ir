# C1 对照臂产出（c1-pilot-2，v1.1）

对照臂直接用 Ascend C 的 C API 手写内核，未使用 IR 工具链。形态按任务书 v1.1 速查第 11–13 条：计算指令末参是 `vmask`，`asc_load(reg, ptr)` / `asc_store(ptr, reg)` 为 2 参，`asc_select(dst, src0, src1, mask)` 掩码在末位，`asc_get_vf_len()` 按 256 字节换算成每轮 64 个 f32。数值、tile 和事件配对未改。

## 自查

| 文件 | 搬运 | 尾块 |
|---|---|---|
| `exp_f32.asc` | 32768 字节 × 512 块 | 4194304 整除 8192；VF 步长 `vf_bytes/4`，`asc_update_mask_b32` 封顶到该步长 |
| `sigmoid_f32.asc` | 同上 | 同上。`asc_ge_scalar` 的比较结果作 `asc_select` 末位掩码 |
| `gelu_f32.asc` | 32768 字节 × 8192 块 | 67108864 整除 8192 |
| `mish_f32.asc` | 32768 字节 × 512 | 与 exp 相同 |
| `masked_scale_f32.asc` | 数据 32768 字节，mask 4096 字节，× 512 | `asc_loadalign_postupdate(pred, uint32_t*&, vf_bytes/8)`，指针由指令推进 |
| `swi_glu_f32.asc` | 每行搬入 16384 字节，写出 8192 字节，2048 行 | 半行 2048 整除 64；x1 起点 `x + i*4096 + 2048` |
| `foreach_addcdiv_f32.asc` | 每个张量 16384 字节，三读一写，512 块 | 2097152 整除 4096 |

事件仍是三对：`PIPE_MTE2→PIPE_V`（`EVENT_ID0`）、`PIPE_V→PIPE_MTE3`（`EVENT_ID1`）、`PIPE_MTE3→PIPE_MTE2`（`EVENT_ID2`），notify 与 wait 参数相同。

token 消耗：口径是任务书第 7 节的会话累计 `completion_tokens`（provider usage），截止点是首次 7 个任务数值门都通过。交卷时数值门尚未跑完，且会话内读不到 Cursor 界面上的 usage 计数，因此未填具体数字。

## workspace/exp_f32.asc

```cpp
#include "c_api/asc_simd.h"

// y = exp(1.5 * x), natural exp. Shape [2048, 2048].
// Tile 8192 f32 = 32768 bytes, under the uint16 copy limit (65535).

__simd_vf__ inline void exp_vf(__ubuf__ float* dst, __ubuf__ float* src, uint32_t len) {
    uint32_t vf_bytes = static_cast<uint32_t>(asc_get_vf_len());
    uint32_t vl = vf_bytes / 4u;
    for (uint32_t i = 0; i < len; i += vl) {
        uint32_t data_len = len - i;
        if (data_len > vl) {
            data_len = vl;
        }
        vector_bool mask = asc_update_mask_b32(data_len);
        vector_float vx;
        asc_load(vx, src + i);
        asc_mul_scalar(vx, vx, 1.5f, mask);
        asc_exp(vx, vx, mask);
        asc_store(dst + i, vx);
    }
}

__vector__ __global__ __aicore__ void exp_f32(__gm__ float* x, __gm__ float* z) {
    asc_init();
    constexpr uint32_t kTotal = 2048u * 2048u;
    constexpr uint32_t kTile = 8192u;
    constexpr uint32_t kPad = 256u;
    static_assert(kTile * 4u <= 65535u, "gm copy exceeds 65535 bytes");
    static_assert(kTotal % kTile == 0u, "tile must divide the tensor");

    __ubuf__ float x_ub[kTile + kPad];
    __ubuf__ float z_ub[kTile + kPad];

    for (uint32_t off = 0; off < kTotal; off += kTile) {
        uint32_t n = kTotal - off;
        if (n > kTile) {
            n = kTile;
        }
        uint16_t nbytes = static_cast<uint16_t>(n * 4u);
        asc_copy_gm2ub(x_ub, x + off, nbytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        exp_vf(z_ub, x_ub, n);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_copy_ub2gm(z + off, z_ub, nbytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
    }
}
```

## workspace/sigmoid_f32.asc

```cpp
#include "c_api/asc_simd.h"

// y = 1 / (1 + exp(-x)). Shape [2048, 2048].
// Stable form: e = exp(-|x|), sigmoid(|x|) = 1/(1+e), sigmoid(-|x|) = e/(1+e).
// Tile 8192 f32 = 32768 bytes, under the uint16 copy limit (65535).

__simd_vf__ inline void sigmoid_vf(__ubuf__ float* dst, __ubuf__ float* src, uint32_t len) {
    uint32_t vf_bytes = static_cast<uint32_t>(asc_get_vf_len());
    uint32_t vl = vf_bytes / 4u;
    for (uint32_t i = 0; i < len; i += vl) {
        uint32_t data_len = len - i;
        if (data_len > vl) {
            data_len = vl;
        }
        vector_bool mask = asc_update_mask_b32(data_len);
        vector_float vx;
        asc_load(vx, src + i);
        vector_float ax;
        asc_abs(ax, vx, mask);
        vector_float neg_ax;
        asc_neg(neg_ax, ax, mask);
        vector_float e;
        asc_exp(e, neg_ax, mask);
        vector_float den;
        asc_add_scalar(den, e, 1.0f, mask);
        vector_float one;
        asc_duplicate_scalar(one, 1.0f, mask);
        vector_float sig_pos;
        asc_div(sig_pos, one, den, mask);
        vector_float sig_neg;
        asc_div(sig_neg, e, den, mask);
        vector_bool pos;
        asc_ge_scalar(pos, vx, 0.0f, mask);
        vector_float sig;
        asc_select(sig, sig_pos, sig_neg, pos);
        asc_store(dst + i, sig);
    }
}

__vector__ __global__ __aicore__ void sigmoid_f32(__gm__ float* x, __gm__ float* z) {
    asc_init();
    constexpr uint32_t kTotal = 2048u * 2048u;
    constexpr uint32_t kTile = 8192u;
    constexpr uint32_t kPad = 256u;
    static_assert(kTile * 4u <= 65535u, "gm copy exceeds 65535 bytes");
    static_assert(kTotal % kTile == 0u, "tile must divide the tensor");

    __ubuf__ float x_ub[kTile + kPad];
    __ubuf__ float z_ub[kTile + kPad];

    for (uint32_t off = 0; off < kTotal; off += kTile) {
        uint32_t n = kTotal - off;
        if (n > kTile) {
            n = kTile;
        }
        uint16_t nbytes = static_cast<uint16_t>(n * 4u);
        asc_copy_gm2ub(x_ub, x + off, nbytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        sigmoid_vf(z_ub, x_ub, n);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_copy_ub2gm(z + off, z_ub, nbytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
    }
}
```

## workspace/gelu_f32.asc

```cpp
#include "c_api/asc_simd.h"

// y = 0.5 * x * (1 + tanh(0.7978845608 * (x + 0.044715 * x^3)))
// tanh(v) = sign(v) * (1 - exp(-2*|v|)) / (1 + exp(-2*|v|))
// Shape [8192, 8192]. Tile 8192 f32 = 32768 bytes (limit 65535).

__simd_vf__ inline void gelu_vf(__ubuf__ float* dst, __ubuf__ float* src, uint32_t len) {
    uint32_t vf_bytes = static_cast<uint32_t>(asc_get_vf_len());
    uint32_t vl = vf_bytes / 4u;
    for (uint32_t i = 0; i < len; i += vl) {
        uint32_t data_len = len - i;
        if (data_len > vl) {
            data_len = vl;
        }
        vector_bool mask = asc_update_mask_b32(data_len);
        vector_float x;
        asc_load(x, src + i);
        vector_float x2;
        asc_mul(x2, x, x, mask);
        vector_float x3;
        asc_mul(x3, x2, x, mask);
        vector_float x3_scaled;
        asc_mul_scalar(x3_scaled, x3, 0.044715f, mask);
        vector_float inner;
        asc_add(inner, x, x3_scaled, mask);
        vector_float arg;
        asc_mul_scalar(arg, inner, 0.7978845608f, mask);

        vector_float ax;
        asc_abs(ax, arg, mask);
        vector_float two_ax;
        asc_mul_scalar(two_ax, ax, 2.0f, mask);
        vector_float neg_two_ax;
        asc_neg(neg_two_ax, two_ax, mask);
        vector_float e;
        asc_exp(e, neg_two_ax, mask);
        vector_float one;
        asc_duplicate_scalar(one, 1.0f, mask);
        vector_float one_minus_e;
        asc_sub(one_minus_e, one, e, mask);
        vector_float den;
        asc_add_scalar(den, e, 1.0f, mask);
        vector_float mag;
        asc_div(mag, one_minus_e, den, mask);
        vector_bool pos;
        asc_ge_scalar(pos, arg, 0.0f, mask);
        vector_float neg_one;
        asc_duplicate_scalar(neg_one, -1.0f, mask);
        vector_float sign;
        asc_select(sign, one, neg_one, pos);
        vector_float th;
        asc_mul(th, mag, sign, mask);

        vector_float half_x;
        asc_mul_scalar(half_x, x, 0.5f, mask);
        vector_float one_plus_th;
        asc_add_scalar(one_plus_th, th, 1.0f, mask);
        vector_float y;
        asc_mul(y, half_x, one_plus_th, mask);
        asc_store(dst + i, y);
    }
}

__vector__ __global__ __aicore__ void gelu_f32(__gm__ float* x, __gm__ float* z) {
    asc_init();
    constexpr uint32_t kTotal = 8192u * 8192u;
    constexpr uint32_t kTile = 8192u;
    constexpr uint32_t kPad = 256u;
    static_assert(kTile * 4u <= 65535u, "gm copy exceeds 65535 bytes");
    static_assert(kTotal % kTile == 0u, "tile must divide the tensor");

    __ubuf__ float x_ub[kTile + kPad];
    __ubuf__ float z_ub[kTile + kPad];

    for (uint32_t off = 0; off < kTotal; off += kTile) {
        uint32_t n = kTotal - off;
        if (n > kTile) {
            n = kTile;
        }
        uint16_t nbytes = static_cast<uint16_t>(n * 4u);
        asc_copy_gm2ub(x_ub, x + off, nbytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        gelu_vf(z_ub, x_ub, n);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_copy_ub2gm(z + off, z_ub, nbytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
    }
}
```

## workspace/mish_f32.asc

```cpp
#include "c_api/asc_simd.h"

// y = x * tanh(ln(1 + exp(x))). Shape [2048, 2048].
// softplus(x) = max(x, 0) + ln(1 + exp(-|x|)), same value as ln(1 + exp(x)).
// tanh via exp(-2*|v|). Tile 8192 f32 = 32768 bytes (limit 65535).

__simd_vf__ inline void mish_vf(__ubuf__ float* dst, __ubuf__ float* src, uint32_t len) {
    uint32_t vf_bytes = static_cast<uint32_t>(asc_get_vf_len());
    uint32_t vl = vf_bytes / 4u;
    for (uint32_t i = 0; i < len; i += vl) {
        uint32_t data_len = len - i;
        if (data_len > vl) {
            data_len = vl;
        }
        vector_bool mask = asc_update_mask_b32(data_len);
        vector_float x;
        asc_load(x, src + i);

        vector_float ax;
        asc_abs(ax, x, mask);
        vector_float neg_ax;
        asc_neg(neg_ax, ax, mask);
        vector_float exp_neg;
        asc_exp(exp_neg, neg_ax, mask);
        vector_float one_plus_exp;
        asc_add_scalar(one_plus_exp, exp_neg, 1.0f, mask);
        vector_float ln_term;
        asc_ln(ln_term, one_plus_exp, mask);
        vector_float relu_x;
        asc_max_scalar(relu_x, x, 0.0f, mask);
        vector_float sp;
        asc_add(sp, relu_x, ln_term, mask);

        vector_float sp_abs;
        asc_abs(sp_abs, sp, mask);
        vector_float two_sp;
        asc_mul_scalar(two_sp, sp_abs, 2.0f, mask);
        vector_float neg_two_sp;
        asc_neg(neg_two_sp, two_sp, mask);
        vector_float e;
        asc_exp(e, neg_two_sp, mask);
        vector_float one;
        asc_duplicate_scalar(one, 1.0f, mask);
        vector_float one_minus_e;
        asc_sub(one_minus_e, one, e, mask);
        vector_float den;
        asc_add_scalar(den, e, 1.0f, mask);
        vector_float mag;
        asc_div(mag, one_minus_e, den, mask);
        vector_bool pos;
        asc_ge_scalar(pos, sp, 0.0f, mask);
        vector_float neg_one;
        asc_duplicate_scalar(neg_one, -1.0f, mask);
        vector_float sign;
        asc_select(sign, one, neg_one, pos);
        vector_float th;
        asc_mul(th, mag, sign, mask);

        vector_float y;
        asc_mul(y, x, th, mask);
        asc_store(dst + i, y);
    }
}

__vector__ __global__ __aicore__ void mish_f32(__gm__ float* x, __gm__ float* z) {
    asc_init();
    constexpr uint32_t kTotal = 2048u * 2048u;
    constexpr uint32_t kTile = 8192u;
    constexpr uint32_t kPad = 256u;
    static_assert(kTile * 4u <= 65535u, "gm copy exceeds 65535 bytes");
    static_assert(kTotal % kTile == 0u, "tile must divide the tensor");

    __ubuf__ float x_ub[kTile + kPad];
    __ubuf__ float z_ub[kTile + kPad];

    for (uint32_t off = 0; off < kTotal; off += kTile) {
        uint32_t n = kTotal - off;
        if (n > kTile) {
            n = kTile;
        }
        uint16_t nbytes = static_cast<uint16_t>(n * 4u);
        asc_copy_gm2ub(x_ub, x + off, nbytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        mish_vf(z_ub, x_ub, n);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_copy_ub2gm(z + off, z_ub, nbytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
    }
}
```

## workspace/masked_scale_f32.asc

```cpp
#include "c_api/asc_simd.h"

// y = select(m, x, 0) * scale, scale = 1.0, m in {0, 1}.
// x, z: [2048, 2048] f32. mask is a bit-packed u8 stream,
// byte count = f32 count * 4 / 8.
// x tile 8192 f32 = 32768 bytes; mask tile = 4096 bytes (limit 65535).

__simd_vf__ inline void masked_scale_vf(__ubuf__ float* dst, __ubuf__ float* src,
                                        __ubuf__ uint8_t* mask, uint32_t len) {
    uint32_t vf_bytes = static_cast<uint32_t>(asc_get_vf_len());
    uint32_t vl = vf_bytes / 4u;
    int32_t mask_rep_size = static_cast<int32_t>(vf_bytes / 8u);
    __ubuf__ uint32_t* mp = (__ubuf__ uint32_t*)mask;
    for (uint32_t i = 0; i < len; i += vl) {
        uint32_t data_len = len - i;
        if (data_len > vl) {
            data_len = vl;
        }
        vector_bool store_mask = asc_update_mask_b32(data_len);
        vector_bool pred;
        asc_loadalign_postupdate(pred, mp, mask_rep_size);
        vector_float vx;
        asc_load(vx, src + i);
        vector_float zero;
        asc_duplicate_scalar(zero, 0.0f, store_mask);
        vector_float vy;
        asc_select(vy, vx, zero, pred);
        asc_mul_scalar(vy, vy, 1.0f, store_mask);
        asc_store(dst + i, vy);
    }
}

__vector__ __global__ __aicore__ void masked_scale_f32(__gm__ float* x, __gm__ uint8_t* mask,
                                                       __gm__ float* z) {
    asc_init();
    constexpr uint32_t kTotal = 2048u * 2048u;
    constexpr uint32_t kTile = 8192u;
    constexpr uint32_t kPad = 256u;
    constexpr uint32_t kMaskTile = kTile * 4u / 8u;
    static_assert(kTile * 4u <= 65535u, "gm copy exceeds 65535 bytes");
    static_assert(kMaskTile <= 65535u, "mask copy exceeds 65535 bytes");
    static_assert(kTotal % kTile == 0u, "tile must divide the tensor");

    __ubuf__ float x_ub[kTile + kPad];
    __ubuf__ float z_ub[kTile + kPad];
    __ubuf__ uint8_t mask_ub[kMaskTile + 256u];

    for (uint32_t off = 0; off < kTotal; off += kTile) {
        uint32_t n = kTotal - off;
        if (n > kTile) {
            n = kTile;
        }
        uint16_t nbytes = static_cast<uint16_t>(n * 4u);
        uint16_t mbytes = static_cast<uint16_t>(n * 4u / 8u);
        uint32_t mask_off = off * 4u / 8u;
        asc_copy_gm2ub(x_ub, x + off, nbytes);
        asc_copy_gm2ub(mask_ub, mask + mask_off, mbytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        masked_scale_vf(z_ub, x_ub, mask_ub, n);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_copy_ub2gm(z + off, z_ub, nbytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
    }
}
```

## workspace/swi_glu_f32.asc

```cpp
#include "c_api/asc_simd.h"

// y = x0 * sigmoid(x0) * x1.
// x is [2048, 4096]; row i holds x0 = x[i, :2048], x1 = x[i, 2048:].
// x1 starts at x + i * 4096 + 2048. z is [2048, 2048].
// One row in: 4096 * 4 = 16384 bytes. One row out: 2048 * 4 = 8192 bytes.

__simd_vf__ inline void swi_glu_vf(__ubuf__ float* dst, __ubuf__ float* x0, __ubuf__ float* x1,
                                   uint32_t len) {
    uint32_t vf_bytes = static_cast<uint32_t>(asc_get_vf_len());
    uint32_t vl = vf_bytes / 4u;
    for (uint32_t i = 0; i < len; i += vl) {
        uint32_t data_len = len - i;
        if (data_len > vl) {
            data_len = vl;
        }
        vector_bool mask = asc_update_mask_b32(data_len);
        vector_float a;
        asc_load(a, x0 + i);
        vector_float b;
        asc_load(b, x1 + i);
        vector_float ax;
        asc_abs(ax, a, mask);
        vector_float neg_ax;
        asc_neg(neg_ax, ax, mask);
        vector_float e;
        asc_exp(e, neg_ax, mask);
        vector_float den;
        asc_add_scalar(den, e, 1.0f, mask);
        vector_float one;
        asc_duplicate_scalar(one, 1.0f, mask);
        vector_float sig_pos;
        asc_div(sig_pos, one, den, mask);
        vector_float sig_neg;
        asc_div(sig_neg, e, den, mask);
        vector_bool pos;
        asc_ge_scalar(pos, a, 0.0f, mask);
        vector_float sig;
        asc_select(sig, sig_pos, sig_neg, pos);
        vector_float a_sig;
        asc_mul(a_sig, a, sig, mask);
        vector_float y;
        asc_mul(y, a_sig, b, mask);
        asc_store(dst + i, y);
    }
}

__vector__ __global__ __aicore__ void swi_glu_f32(__gm__ float* x, __gm__ float* z) {
    asc_init();
    constexpr uint32_t kRows = 2048u;
    constexpr uint32_t kHalf = 2048u;
    constexpr uint32_t kRow = 4096u;
    constexpr uint32_t kPad = 256u;
    static_assert(kRow * 4u <= 65535u, "row copy exceeds 65535 bytes");
    static_assert(kHalf * 4u <= 65535u, "store exceeds 65535 bytes");

    __ubuf__ float x_ub[kRow + kPad];
    __ubuf__ float z_ub[kHalf + kPad];

    for (uint32_t row = 0; row < kRows; row++) {
        uint16_t in_bytes = static_cast<uint16_t>(kRow * 4u);
        uint16_t out_bytes = static_cast<uint16_t>(kHalf * 4u);
        asc_copy_gm2ub(x_ub, x + row * kRow, in_bytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        swi_glu_vf(z_ub, x_ub, x_ub + kHalf, kHalf);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_copy_ub2gm(z + row * kHalf, z_ub, out_bytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
    }
}
```

## workspace/foreach_addcdiv_f32.asc

```cpp
#include "c_api/asc_simd.h"

// y = x1 + (x2 / x3) * scalar, scalar = 1.0.
// Each parent tensor is contiguous [2, 1024, 1024]; both foreach
// members share this elementwise formula, so the flat length is 2*1024*1024.
// Tile 4096 f32 = 16384 bytes per tensor (limit 65535). Four UB buffers.

__simd_vf__ inline void addcdiv_vf(__ubuf__ float* dst, __ubuf__ float* x1, __ubuf__ float* x2,
                                   __ubuf__ float* x3, uint32_t len) {
    uint32_t vf_bytes = static_cast<uint32_t>(asc_get_vf_len());
    uint32_t vl = vf_bytes / 4u;
    for (uint32_t i = 0; i < len; i += vl) {
        uint32_t data_len = len - i;
        if (data_len > vl) {
            data_len = vl;
        }
        vector_bool mask = asc_update_mask_b32(data_len);
        vector_float a;
        asc_load(a, x1 + i);
        vector_float b;
        asc_load(b, x2 + i);
        vector_float c;
        asc_load(c, x3 + i);
        vector_float q;
        asc_div(q, b, c, mask);
        asc_mul_scalar(q, q, 1.0f, mask);
        vector_float y;
        asc_add(y, a, q, mask);
        asc_store(dst + i, y);
    }
}

__vector__ __global__ __aicore__ void foreach_addcdiv_f32(__gm__ float* x1, __gm__ float* x2,
                                                          __gm__ float* x3, __gm__ float* z) {
    asc_init();
    constexpr uint32_t kTotal = 2u * 1024u * 1024u;
    constexpr uint32_t kTile = 4096u;
    constexpr uint32_t kPad = 256u;
    static_assert(kTile * 4u <= 65535u, "gm copy exceeds 65535 bytes");
    static_assert(kTotal % kTile == 0u, "tile must divide the tensor");

    __ubuf__ float x1_ub[kTile + kPad];
    __ubuf__ float x2_ub[kTile + kPad];
    __ubuf__ float x3_ub[kTile + kPad];
    __ubuf__ float z_ub[kTile + kPad];

    for (uint32_t off = 0; off < kTotal; off += kTile) {
        uint32_t n = kTotal - off;
        if (n > kTile) {
            n = kTile;
        }
        uint16_t nbytes = static_cast<uint16_t>(n * 4u);
        asc_copy_gm2ub(x1_ub, x1 + off, nbytes);
        asc_copy_gm2ub(x2_ub, x2 + off, nbytes);
        asc_copy_gm2ub(x3_ub, x3 + off, nbytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        addcdiv_vf(z_ub, x1_ub, x2_ub, x3_ub, n);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID1);
        asc_copy_ub2gm(z + off, z_ub, nbytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID2);
    }
}
```
