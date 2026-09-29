/**
 * reduce_sum_f32: sum 256 float32 values into 8 output lanes.
 * Host sums those 8 lanes. Pattern follows the 3510 reg reduce sample.
 */
#include <stdint.h>

#include "c_api/asc_simd.h"
#include "reduce_sum_f32_launch.h"

constexpr uint32_t kLength = 256;
constexpr uint32_t kOutLength = 8;

__simd_vf__ inline void reduce_sum_f32_vf(
    __ubuf__ float* x_local, __ubuf__ float* y_local, uint32_t data_len, uint16_t one_rep_size, uint16_t repeat_time)
{
    vector_bool vmask;
    vector_float src_reg;
    vector_float dst_reg;
    vector_float acc_reg;
    asc_duplicate_scalar(acc_reg, 0.0f);
    for (uint16_t i = 0; i < repeat_time; ++i) {
        vmask = asc_update_mask_b32(data_len);
        asc_loadalign(src_reg, x_local + i * one_rep_size);
        asc_reduce_sum(dst_reg, src_reg, vmask);
        asc_add(acc_reg, acc_reg, dst_reg, vmask);
    }
    asc_storealign(y_local, acc_reg, vmask);
}

__vector__ __global__ void reduce_sum_f32_kernel(__gm__ float* x, __gm__ float* y)
{
    asc_init();
    __ubuf__ float x_local[kLength];
    __ubuf__ float y_local[kOutLength];
    asc_copy_gm2ub(x_local, x, kLength * sizeof(float));
    asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
    asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
    const uint16_t one_rep_size = static_cast<uint16_t>(asc_get_vf_len() / sizeof(float));
    const uint16_t repeat_time = static_cast<uint16_t>((kLength + one_rep_size - 1U) / one_rep_size);
    reduce_sum_f32_vf(x_local, y_local, kLength, one_rep_size, repeat_time);
    asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID0);
    asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID0);
    asc_copy_ub2gm(y, y_local, kOutLength * sizeof(float));
}

extern "C" void launch_reduce_sum_f32_kernel(GM_ADDR x, GM_ADDR y, void* stream)
{
    reduce_sum_f32_kernel<<<1, 0, stream>>>((__gm__ float*)x, (__gm__ float*)y);
}
