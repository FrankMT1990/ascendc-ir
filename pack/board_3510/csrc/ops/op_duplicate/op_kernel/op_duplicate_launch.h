#ifndef OP_DUPLICATE_LAUNCH_H
#define OP_DUPLICATE_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_duplicate(GM_ADDR z, void* stream);
}

#endif
