#ifndef OP_MIN_SCALAR_LAUNCH_H
#define OP_MIN_SCALAR_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_min_scalar(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
