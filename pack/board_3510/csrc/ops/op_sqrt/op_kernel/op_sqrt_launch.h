#ifndef OP_SQRT_LAUNCH_H
#define OP_SQRT_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_sqrt(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
