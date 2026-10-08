if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SKIP")
    message(STATUS "Skip op_select_eq")
    return()
endif()
set(OP_SELECT_EQ_KERNEL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/op_select_eq_kernel.cpp)
set(OP_SELECT_EQ_PLUGIN_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/op_select_eq_plugin.cpp)
register_direct_launch_op(
    "${OP_SELECT_EQ_KERNEL_SRCS}" op_kernel
    "${OP_SELECT_EQ_PLUGIN_SRCS}" op_kernel
)
