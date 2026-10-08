if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_mul")
    return()
endif()
set(OP_MUL_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_mul_kernel.cpp)
set(OP_MUL_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_mul_plugin.cpp)
register_direct_launch_op(
    "${OP_MUL_KERNEL_SRCS}" op_kernel
    "${OP_MUL_PLUGIN_SRCS}" op_kernel
)
