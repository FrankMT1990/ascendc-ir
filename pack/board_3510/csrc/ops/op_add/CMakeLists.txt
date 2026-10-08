if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_add")
    return()
endif()
set(OP_ADD_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_add_kernel.cpp)
set(OP_ADD_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_add_plugin.cpp)
register_direct_launch_op(
    "${OP_ADD_KERNEL_SRCS}" op_kernel
    "${OP_ADD_PLUGIN_SRCS}" op_kernel
)
