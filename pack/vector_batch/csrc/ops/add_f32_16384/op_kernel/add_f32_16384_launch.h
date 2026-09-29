#ifndef ADD_F32_16384_LAUNCH_H
#define ADD_F32_16384_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_add_f32_16384_kernel(GM_ADDR x, GM_ADDR y, GM_ADDR z, void* stream);
}

#endif
