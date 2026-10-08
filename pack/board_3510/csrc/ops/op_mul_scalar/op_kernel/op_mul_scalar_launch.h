#ifndef OP_MUL_SCALAR_LAUNCH_H
#define OP_MUL_SCALAR_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_mul_scalar(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
