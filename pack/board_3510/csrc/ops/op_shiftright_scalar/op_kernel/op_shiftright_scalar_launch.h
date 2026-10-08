#ifndef OP_SHIFTRIGHT_SCALAR_LAUNCH_H
#define OP_SHIFTRIGHT_SCALAR_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_shiftright_scalar(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
