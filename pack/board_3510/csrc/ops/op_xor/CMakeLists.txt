if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_xor")
    return()
endif()
set(OP_XOR_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_xor_kernel.cpp)
set(OP_XOR_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_xor_plugin.cpp)
register_direct_launch_op(
    "${OP_XOR_KERNEL_SRCS}" op_kernel
    "${OP_XOR_PLUGIN_SRCS}" op_kernel
)
