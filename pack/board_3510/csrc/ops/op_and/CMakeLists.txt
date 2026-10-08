if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_and")
    return()
endif()
set(OP_AND_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_and_kernel.cpp)
set(OP_AND_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_and_plugin.cpp)
register_direct_launch_op(
    "${OP_AND_KERNEL_SRCS}" op_kernel
    "${OP_AND_PLUGIN_SRCS}" op_kernel
)
