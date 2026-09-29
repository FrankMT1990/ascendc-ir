/**
 * add_f32_16384 — single-core RegBase add, z = x + y, 16384 float32.
 *
 * Vector body follows the dav-3510 sample
 * asc-devkit/examples/02_simd_c_api/00_introduction/04_reg_base_add_compute/c_api_simd_add/c_api_add.asc
 * (asc_load / asc_add on vector_float / asc_store / asc_update_mask_b32).
 *
 * That sample splits 16384 elements across 8 blocks of 2048. This kernel keeps
 * the same 2048-element tile and runs the tiles on one block. Each GM↔UB copy
 * is 8192 bytes. The 3510 size overload of asc_copy_gm2ub / asc_copy_ub2gm
 * forwards size into uint16_t burst_len (max 65535); 16384 float32 is 65536
 * bytes, so one copy of the full tensor does not fit that implementation.
 */
#include <stdint.h>

#include "c_api/asc_simd.h"
#include "add_f32_16384_launch.h"

constexpr uint32_t kTotalLength = 16384;
constexpr uint32_t kTileLength = 2048;

__simd_vf__ inline void add_f32_16384_vf(
    __ubuf__ float* x_local, __ubuf__ float* y_local, __ubuf__ float* z_local, uint32_t num_elems)
{
    const uint16_t repeat_elems = static_cast<uint16_t>(asc_get_vf_len() / sizeof(float));
    const uint16_t num_repeats = static_cast<uint16_t>((num_elems + repeat_elems - 1U) / repeat_elems);

    vector_bool vmask;
    vector_float src0;
    vector_float src1;
    vector_float dst;
    for (uint16_t i = 0; i < num_repeats; ++i) {
        vmask = asc_update_mask_b32(num_elems);
        asc_load(src0, x_local + i * repeat_elems);
        asc_load(src1, y_local + i * repeat_elems);
        asc_add(dst, src0, src1, vmask);
        asc_store(z_local + i * repeat_elems, dst);
    }
}

__vector__ __global__ void add_f32_16384_kernel(__gm__ float* x, __gm__ float* y, __gm__ float* z)
{
    asc_init();

    constexpr uint32_t tile_byte_size = kTileLength * sizeof(float);
    constexpr uint8_t mutex_id = 1;

    __ubuf__ float x_local[kTileLength];
    __ubuf__ float y_local[kTileLength];
    __ubuf__ float z_local[kTileLength];

    for (uint32_t offset = 0; offset < kTotalLength; offset += kTileLength) {
        __gm__ float* x_gm = x + offset;
        __gm__ float* y_gm = y + offset;
        __gm__ float* z_gm = z + offset;

        asc_lock(PIPE_MTE2, mutex_id);
        asc_copy_gm2ub(x_local, x_gm, tile_byte_size);
        asc_copy_gm2ub(y_local, y_gm, tile_byte_size);
        asc_unlock(PIPE_MTE2, mutex_id);

        asc_lock(PIPE_V, mutex_id);
        add_f32_16384_vf(
            (__ubuf__ float*)x_local, (__ubuf__ float*)y_local, (__ubuf__ float*)z_local, kTileLength);
        asc_unlock(PIPE_V, mutex_id);

        asc_lock(PIPE_MTE3, mutex_id);
        asc_copy_ub2gm(z_gm, z_local, tile_byte_size);
        asc_unlock(PIPE_MTE3, mutex_id);
    }
}

extern "C" void launch_add_f32_16384_kernel(GM_ADDR x, GM_ADDR y, GM_ADDR z, void* stream)
{
    add_f32_16384_kernel<<<1, 0, stream>>>((__gm__ float*)x, (__gm__ float*)y, (__gm__ float*)z);
}
