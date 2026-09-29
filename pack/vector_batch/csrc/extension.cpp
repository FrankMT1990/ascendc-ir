#ifndef TORCH_EXTENSION_NAME
#define TORCH_EXTENSION_NAME _C
#endif

#include <torch/extension.h>

// Plugin objects register torch.ops.cann_bench.add_f32_16384 via TORCH_LIBRARY
// static initializers. This translation unit is the Python module entry.
PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {}
