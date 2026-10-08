if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_repeat_reduce_sum")
    return()
endif()
set(OP_REPEAT_REDUCE_SUM_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_repeat_reduce_sum_kernel.cpp)
set(OP_REPEAT_REDUCE_SUM_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_repeat_reduce_sum_plugin.cpp)
register_direct_launch_op(
    "${OP_REPEAT_REDUCE_SUM_KERNEL_SRCS}" op_kernel
    "${OP_REPEAT_REDUCE_SUM_PLUGIN_SRCS}" op_kernel
)
