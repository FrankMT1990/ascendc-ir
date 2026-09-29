#ifndef REDUCE_SUM_F32_LAUNCH_H
#define REDUCE_SUM_F32_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_reduce_sum_f32_kernel(GM_ADDR x, GM_ADDR y, void* stream);
}

#endif
