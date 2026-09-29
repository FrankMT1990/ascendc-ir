#ifndef CAST_HALF_TO_FLOAT_LAUNCH_H
#define CAST_HALF_TO_FLOAT_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_cast_half_to_float_kernel(GM_ADDR x, GM_ADDR y, void* stream);
}

#endif
