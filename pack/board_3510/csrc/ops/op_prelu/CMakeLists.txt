if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_prelu")
    return()
endif()
set(OP_PRELU_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_prelu_kernel.cpp)
set(OP_PRELU_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_prelu_plugin.cpp)
register_direct_launch_op(
    "${OP_PRELU_KERNEL_SRCS}" op_kernel
    "${OP_PRELU_PLUGIN_SRCS}" op_kernel
)
