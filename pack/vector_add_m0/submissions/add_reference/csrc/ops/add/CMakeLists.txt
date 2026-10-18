# ----------------------------------------------------------------------------------------------------------
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This file is part of the M0 handwritten-reference submission (see ADR 0014).
# ----------------------------------------------------------------------------------------------------------

# add 算子自注册（M0 候选：codegen 生成版）

# Kernel源文件(bisheng编译: --npu-arch=dav-3510 --asc-aicore-lang)
set(ADD_KERNEL_SRCS
    ${CMAKE_CURRENT_SOURCE_DIR}/op_kernel/add_kernel.cpp
)

# Plugin源文件(无 -xasc/--asc-aicore-lang 的 C++ 编译)
set(ADD_PLUGIN_SRCS
    ${CMAKE_CURRENT_SOURCE_DIR}/op_plugin/add_plugin.cpp
)

# 注册到全局列表
register_direct_launch_op(
    "${ADD_KERNEL_SRCS}"
    op_kernel
    "${ADD_PLUGIN_SRCS}"
    op_plugin
)
