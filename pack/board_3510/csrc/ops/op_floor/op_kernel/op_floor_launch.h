#ifndef OP_FLOOR_LAUNCH_H
#define OP_FLOOR_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_floor(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
