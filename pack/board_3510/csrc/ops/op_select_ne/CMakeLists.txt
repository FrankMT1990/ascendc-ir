if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_select_ne")
    return()
endif()
set(OP_SELECT_NE_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_select_ne_kernel.cpp)
set(OP_SELECT_NE_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_select_ne_plugin.cpp)
register_direct_launch_op(
    "${OP_SELECT_NE_KERNEL_SRCS}" op_kernel
    "${OP_SELECT_NE_PLUGIN_SRCS}" op_kernel
)
