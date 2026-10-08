if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_leakyrelu")
    return()
endif()
set(OP_LEAKYRELU_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_leakyrelu_kernel.cpp)
set(OP_LEAKYRELU_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_leakyrelu_plugin.cpp)
register_direct_launch_op(
    "${OP_LEAKYRELU_KERNEL_SRCS}" op_kernel
    "${OP_LEAKYRELU_PLUGIN_SRCS}" op_kernel
)
