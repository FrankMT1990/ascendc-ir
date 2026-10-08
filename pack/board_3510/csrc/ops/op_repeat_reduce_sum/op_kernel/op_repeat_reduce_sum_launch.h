#ifndef OP_REPEAT_REDUCE_SUM_LAUNCH_H
#define OP_REPEAT_REDUCE_SUM_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_repeat_reduce_sum(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
