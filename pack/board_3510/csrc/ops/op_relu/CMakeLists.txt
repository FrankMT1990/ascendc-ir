if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_relu")
    return()
endif()
set(OP_RELU_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_relu_kernel.cpp)
set(OP_RELU_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_relu_plugin.cpp)
register_direct_launch_op(
    "${OP_RELU_KERNEL_SRCS}" op_kernel
    "${OP_RELU_PLUGIN_SRCS}" op_kernel
)
