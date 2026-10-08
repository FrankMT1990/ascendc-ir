if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_ln")
    return()
endif()
set(OP_LN_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_ln_kernel.cpp)
set(OP_LN_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_ln_plugin.cpp)
register_direct_launch_op(
    "${OP_LN_KERNEL_SRCS}" op_kernel
    "${OP_LN_PLUGIN_SRCS}" op_kernel
)
