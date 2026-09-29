/**
 * cast_half_to_float: 1024 float16 -> 1024 float32, one core.
 *
 * 3510 native CANN 9.1.0 pattern (asc-devkit 的 asc_loadalign_unpack / ASC_POSITION_EVEN
 * 不存在于原生 c_api 树；原生等价 = UNPK 装载 + PART_EVEN 转换，与 CANN 自带
 * Cast Level-2 实现一致: asc/impl/basic_api/dav_m310/kernel_operator_vec_vconv_impl.h
 * 的 LV2_LOAD_UPPER 用 vlds(src, i*64, UNPK_B16)，VCVT_F16_TO_F32 用 vcvt PART_EVEN):
 *   vlds(src, x + i*64, 0, UNPK_B16)  装载 64 个 half 解包进偶位槽
 *   asc_half2float(dst, src, vmask)   即 vcvt PART_EVEN，按序转换偶位 64 个
 *   asc_storealign(y + i*64, dst, vmask)
 */
#include <stdint.h>

#include "c_api/asc_simd.h"
#include "cast_half_to_float_launch.h"

constexpr uint32_t kLength = 1024;

__simd_vf__ inline void cast_half_to_float_vf(__ubuf__ half* x_local, __ubuf__ float* y_local, uint32_t num_elems)
{
    const uint16_t repeat_elems = static_cast<uint16_t>(asc_get_vf_len() / sizeof(float));
    const uint16_t num_repeats = static_cast<uint16_t>((num_elems + repeat_elems - 1U) / repeat_elems);
    vector_bool vmask;
    vector_half src;
    vector_float dst;
    for (uint16_t i = 0; i < num_repeats; ++i) {
        vmask = asc_update_mask_b32(num_elems);
        vlds(src, x_local + i * repeat_elems, 0, UNPK_B16);
        asc_half2float(dst, src, vmask);
        asc_storealign(y_local + i * repeat_elems, dst, vmask);
    }
}

__vector__ __global__ void cast_half_to_float_kernel(__gm__ half* x, __gm__ float* y)
{
    asc_init();
    __ubuf__ half x_local[kLength];
    __ubuf__ float y_local[kLength];
    asc_copy_gm2ub(x_local, x, kLength * sizeof(half));
    asc_sync_notify(PIPE_MTE2, PIPE_V, EVENT_ID0);
    asc_sync_wait(PIPE_MTE2, PIPE_V, EVENT_ID0);
    cast_half_to_float_vf(x_local, y_local, kLength);
    asc_sync_notify(PIPE_V, PIPE_MTE3, EVENT_ID0);
    asc_sync_wait(PIPE_V, PIPE_MTE3, EVENT_ID0);
    asc_copy_ub2gm(y, y_local, kLength * sizeof(float));
}

extern "C" void launch_cast_half_to_float_kernel(GM_ADDR x, GM_ADDR y, void* stream)
{
    cast_half_to_float_kernel<<<1, 0, stream>>>((__gm__ half*)x, (__gm__ float*)y);
}
