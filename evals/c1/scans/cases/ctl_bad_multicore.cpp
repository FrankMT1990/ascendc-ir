extern "C" void launch_bad(int blocks, void** streams)
{
    for (int block_idx = 0; block_idx < blocks; ++block_idx) {
        dispatch_kernel(block_idx, streams[block_idx]);
    }
}
