if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_exp")
    return()
endif()
set(OP_EXP_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_exp_kernel.cpp)
set(OP_EXP_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_exp_plugin.cpp)
register_direct_launch_op(
    "${OP_EXP_KERNEL_SRCS}" op_kernel
    "${OP_EXP_PLUGIN_SRCS}" op_kernel
)
