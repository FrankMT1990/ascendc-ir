if(NOT Python3_EXECUTABLE)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
endif()

execute_process(
    COMMAND ${Python3_EXECUTABLE} -c "import os, torch_npu; print(os.path.dirname(torch_npu.__file__))"
    OUTPUT_STRIP_TRAILING_WHITESPACE
    OUTPUT_VARIABLE TORCH_NPU_PATH
    RESULT_VARIABLE _torch_npu_probe
)
if(NOT _torch_npu_probe EQUAL 0)
    message(FATAL_ERROR "failed to import torch_npu")
endif()
set(TORCH_NPU_INCLUDE_DIRS "${TORCH_NPU_PATH}/include")
set(TORCH_NPU_LIBRARIES "${TORCH_NPU_PATH}/lib")
message(STATUS "torch_npu: ${TORCH_NPU_PATH}")
