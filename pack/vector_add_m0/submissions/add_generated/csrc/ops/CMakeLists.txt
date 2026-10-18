# ----------------------------------------------------------------------------
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This file is part of the ascendc-ir M0 measurement pack.
# ----------------------------------------------------------------------------

# 自动发现并添加所有算子目录
file(GLOB SUB_DIRS LIST_DIRECTORIES true ${CMAKE_CURRENT_SOURCE_DIR}/*)

foreach(SUB_DIR ${SUB_DIRS})
    if(IS_DIRECTORY ${SUB_DIR})
        get_filename_component(DIR_NAME ${SUB_DIR} NAME)
        message(STATUS "Adding op directory: ${DIR_NAME}")
        add_subdirectory(${SUB_DIR})
    endif()
endforeach()
