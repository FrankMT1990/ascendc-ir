/**
 * leakyrelu_f32: y = x if x > 0 else 0.1 * x. 16384 float32, one core.
 * 3510 reg API: asc_leakyrelu(vector_float&, vector_float, float, vector_bool).
 */
#include <stdint.h>

#include "c_api/asc_simd.h"
#include "leakyrelu_f32_launch.h"

constexpr uint32_t kTotalLength = 16384;
constexpr uint32_t kTileLength = 2048;
constexpr float kAlpha = 0.1f;

__simd_vf__ inline void leakyrelu_f32_vf(__ubuf__ float* x_local, __ubuf__ float* y_local, uint32_t num_elems)
{
    const uint16_t repeat_elems = static_cast<uint16_t>(asc_get_vf_len() / sizeof(float));
    const uint16_t num_repeats = static_cast<uint16_t>((num_elems + repeat_elems - 1U) / repeat_elems);
    vector_bool vmask;
    vector_float src;
    vector_float dst;
    for (uint16_t i = 0; i < num_repeats; ++i) {
        vmask = asc_update_mask_b32(num_elems);
        asc_load(src, x_local + i * repeat_elems);
        asc_leakyrelu(dst, src, kAlpha, vmask);
        asc_store(y_local + i * repeat_elems, dst);
    }
}

__vector__ __global__ void leakyrelu_f32_kernel(__gm__ float* x, __gm__ float* y)
{
    asc_init();
    constexpr uint32_t tile_bytes = kTileLength * sizeof(float);
    __ubuf__ float x_local[kTileLength];
    __ubuf__ float y_local[kTileLength];
    for (uint32_t offset = 0; offset < kTotalLength; offset += kTileLength) {
        asc_copy_gm2ub(x_local, x + offset, tile_bytes);
        asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
        asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
        leakyrelu_f32_vf(x_local, y_local, kTileLength);
        asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID0);
        asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID0);
        asc_copy_ub2gm(y + offset, y_local, tile_bytes);
        asc_sync_notify(PIPE_MTE3, PIPE_MTE2, EVENT_ID0);
        asc_sync_wait(PIPE_MTE3, PIPE_MTE2, EVENT_ID0);
    }
}

extern "C" void launch_leakyrelu_f32_kernel(GM_ADDR x, GM_ADDR y, void* stream)
{
    leakyrelu_f32_kernel<<<1, 0, stream>>>((__gm__ float*)x, (__gm__ float*)y);
}
