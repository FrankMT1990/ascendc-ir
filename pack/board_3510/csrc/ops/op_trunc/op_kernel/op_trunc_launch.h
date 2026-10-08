#ifndef OP_TRUNC_LAUNCH_H
#define OP_TRUNC_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_trunc(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
