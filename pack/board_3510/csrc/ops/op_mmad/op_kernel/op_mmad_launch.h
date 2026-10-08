#ifndef OP_MMAD_LAUNCH_H
#define OP_MMAD_LAUNCH_H

#ifndef GM_ADDR
#define GM_ADDR void*
#endif

extern "C" {
void launch_op_mmad(GM_ADDR a, GM_ADDR b, GM_ADDR c, void* stream);
}

#endif
