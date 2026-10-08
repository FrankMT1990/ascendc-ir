#ifndef OP_SELECT_GE_SCALAR_LAUNCH_H
#define OP_SELECT_GE_SCALAR_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_select_ge_scalar(GM_ADDR x, GM_ADDR y, GM_ADDR z, void* stream);
}

#endif
