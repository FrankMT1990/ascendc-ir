#ifndef OP_ADD_LAUNCH_H
#define OP_ADD_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_add(GM_ADDR x, GM_ADDR y, GM_ADDR z, void* stream);
}

#endif
