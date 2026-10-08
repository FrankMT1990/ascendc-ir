if(NOT Python3_EXECUTABLE)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
endif()

execute_process(
    COMMAND ${Python3_EXECUTABLE} -c "import torch; print(torch.utils.cmake_prefix_path)"
    OUTPUT_STRIP_TRAILING_WHITESPACE
    OUTPUT_VARIABLE TORCH_CMAKE_PREFIX_PATH
    RESULT_VARIABLE _torch_probe
)
if(NOT _torch_probe EQUAL 0)
    message(FATAL_ERROR "failed to import torch")
endif()
find_package(Torch REQUIRED HINTS ${TORCH_CMAKE_PREFIX_PATH})
message(STATUS "Torch: ${TORCH_CMAKE_PREFIX_PATH}")
