#ifndef LEAKYRELU_F32_LAUNCH_H
#define LEAKYRELU_F32_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_leakyrelu_f32_kernel(GM_ADDR x, GM_ADDR y, void* stream);
}

#endif
