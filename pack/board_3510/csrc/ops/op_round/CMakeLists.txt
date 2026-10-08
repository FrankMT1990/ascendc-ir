if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_round")
    return()
endif()
set(OP_ROUND_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_round_kernel.cpp)
set(OP_ROUND_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_round_plugin.cpp)
register_direct_launch_op(
    "${OP_ROUND_KERNEL_SRCS}" op_kernel
    "${OP_ROUND_PLUGIN_SRCS}" op_kernel
)
