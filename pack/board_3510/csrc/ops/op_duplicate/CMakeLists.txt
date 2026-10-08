if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_duplicate")
    return()
endif()
set(OP_DUPLICATE_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_duplicate_kernel.cpp)
set(OP_DUPLICATE_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_duplicate_plugin.cpp)
register_direct_launch_op(
    "${OP_DUPLICATE_KERNEL_SRCS}" op_kernel
    "${OP_DUPLICATE_PLUGIN_SRCS}" op_kernel
)
