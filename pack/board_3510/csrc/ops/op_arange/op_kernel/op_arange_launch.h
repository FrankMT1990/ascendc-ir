#ifndef OP_ARANGE_LAUNCH_H
#define OP_ARANGE_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_arange(GM_ADDR z, void* stream);
}

#endif
