#ifndef OP_RINT_LAUNCH_H
#define OP_RINT_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_rint(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
