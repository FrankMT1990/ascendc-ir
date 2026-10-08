if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_neg")
    return()
endif()
set(OP_NEG_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_neg_kernel.cpp)
set(OP_NEG_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_neg_plugin.cpp)
register_direct_launch_op(
    "${OP_NEG_KERNEL_SRCS}" op_kernel
    "${OP_NEG_PLUGIN_SRCS}" op_kernel
)
