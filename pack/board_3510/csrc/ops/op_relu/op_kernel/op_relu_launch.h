#ifndef OP_RELU_LAUNCH_H
#define OP_RELU_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_relu(GM_ADDR x, GM_ADDR z, void* stream);
}

#endif
