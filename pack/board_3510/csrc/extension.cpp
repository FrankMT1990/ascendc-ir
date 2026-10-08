#ifndef TORCH_EXTENSION_NAME
#define TORCH_EXTENSION_NAME _C
#endif

#include <torch/extension.h>

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {}
