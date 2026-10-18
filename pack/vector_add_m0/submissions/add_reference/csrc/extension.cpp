/**
 * Copyright (c) 2026 Huawei Technologies Co., Ltd.
 * This file is part of the M0 handwritten-reference submission (see ADR 0014).
 * See LICENSE in the root of the software repository for the full text of the License.
 */

/*!
 * \file extension.cpp
 * \brief 载入 _C 模块以运行 TORCH_LIBRARY 静态注册器
 */

#include <Python.h>

extern "C"
{
    PyObject *PyInit__C(void)
    {
        static struct PyModuleDef module_def = {
            PyModuleDef_HEAD_INIT,
            "_C",
            NULL,
            -1,
            NULL,
        };
        return PyModule_Create(&module_def);
    }
}
