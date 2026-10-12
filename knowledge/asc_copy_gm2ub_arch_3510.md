---
type: API
title: asc_copy_gm2ub
description: 将数据从Global Memory (GM) 搬运到 Unified Buffer（UB）。
tags:
- task.lookup
- topic.implementation.api_layer.c_api
status: stable
sources:
- resource: cann-docs-raw/asc-devkit/docs/zh/api/SIMD-API/c_api/vector_datamove/asc_copy_gm2ub/asc_copy_gm2ub_arch_3510.md
  role: primary
created_at: '2026-09-03T08:52:46Z'
updated_at: '2026-09-12T03:09:26Z'
platforms:
- '950'
source_headers:
- include/c_api/vector_datamove/vector_datamove.h
- include/c_api/asc_simd.h
---

# asc_copy_gm2ub

## 功能说明

头文件路径为：`"c_api/vector_datamove/vector_datamove.h"`。

将数据从Global Memory（GM）搬运到Unified Buffer（UB）。

本接口支持连续数据搬运和高维切分数据搬运。连续数据搬运按`size`指定的字节数从源GM连续搬运到目的UB，如图1所示；高维切分数据搬运按`burst_count`指定搬运的数据块个数，每个数据块按`burst_len`指定的字节数搬运，并通过`src_stride`和`dst_stride`指定源操作数和目的操作数相邻数据块首地址间隔，如图2所示。

**图1**  连续搬运示意图

![](https://raw.gitcode.com/cann/asc-devkit/raw/639b2b5c1031188107d23d785d52b935f1b4f13b/docs/zh/api/SIMD-API/c_api/figures/asc_copy_gm2ub_continuous.png "连续搬运示意图")

**图2**  高维切分搬运示意图

![](https://raw.gitcode.com/cann/asc-devkit/raw/639b2b5c1031188107d23d785d52b935f1b4f13b/docs/zh/api/SIMD-API/c_api/figures/asc_copy_gm2ub_highdim_split.png "高维切分搬运示意图")

本接口仅在AIV上生效。

## 函数原型

### 连续数据搬运

```c
__aicore__ inline void asc_copy_gm2ub(__ubuf__ void* dst,
                                      __gm__ void* src,
                                      uint32_t size)
```

### 高维切分数据搬运

```c
__aicore__ inline void asc_copy_gm2ub(__ubuf__ void* dst,
                                      __gm__ void* src,
                                      uint16_t burst_count,
                                      uint16_t burst_len,
                                      uint16_t src_stride,
                                      uint16_t dst_stride)
```

## 参数说明

### 连续数据搬运

**表1** 参数说明

| 参数名 | 输入/输出 | 描述 |
| :--- | :--- | :--- |
| dst | 输出 | 目的UB的起始地址。需要32字节对齐。 |
| src | 输入 | 源GM的起始地址。需要1字节对齐。 |
| size | 输入 | 搬运数据大小，单位为字节。取值范围：[1, $2^{21}−1$]。 |

### 高维切分数据搬运

**表2** 参数说明

| 参数名 | 输入/输出 | 描述 |
| :--- | :--- | :--- |
| dst | 输出 | 目的UB的起始地址。需要32字节对齐。 |
| src | 输入 | 源GM的起始地址。需要1字节对齐。 |
| burst_count | 输入 | 待搬运的连续传输数据块个数。取值范围：[1, $2^{16}−1$]。 |
| burst_len | 输入 | 待搬运的每个连续传输数据块的长度，单位为字节。取值范围：[1, $2^{16}−1$]。 |
| src_stride | 输入 | 源操作数相邻连续数据块的距离（前面一个数据块的头与后面一个数据块的头的间隔），单位为字节。取值范围：[0, $2^{16}−1$]。<br>只搬运1个数据块，即`burst_count`设置为1时，可以将此参数设置为0。 |
| dst_stride | 输入 | 目的操作数相邻连续数据块的距离（前面一个数据块的头与后面一个数据块的头的间隔），单位为字节。取值范围：[0, $2^{16}−1$]。<br>只搬运1个数据块，即`burst_count`设置为1时，可以将此参数设置为0。 |

## 返回值说明

无

## 流水类型

PIPE_MTE2

## 约束说明

### 通用约束

- 本接口在非AIV上调用直接返回。
- 各存储单元的空间大小和对齐要求请参考[存储单元说明](../../general_description_and_constraints.md#存储单元说明)。
- 如果本指令与其他指令存在UB地址重叠，必须插入同步指令[asc_sync_notify](../../sync/asc_sync_notify.md)和[asc_sync_wait](../../sync/asc_sync_wait.md)，保证多个指令串行化，防止出现异常数据。

### 连续数据搬运约束

- `size`需满足dtype字节对齐：dtype为b16时需为2的倍数，dtype为b32时需为4的倍数。

### 高维切分数据搬运约束

- `burst_len`需满足dtype字节对齐：dtype为b16时需为2的倍数，dtype为b32时需为4的倍数。
- 当`dst_stride`不等于`burst_len`时，`dst_stride`要求32字节对齐。

## 调用示例

将代码保存为`example.asc`后，可通过`bisheng`命令编译运行，其中`--npu-arch`参数需根据实际产品型号指定对应的NPU架构，具体产品与NPU架构的映射关系请参考[\_\_NPU\_ARCH\_\_](../../../../../guides/programming_guide/language_extension/simd_builtin_keywords.md#npu-arch)。


以Ascend 950PR/Ascend 950DT产品（对应NPU架构为`dav-3510`）为例，编译运行命令如下：

```bash
bisheng example.asc -o main --npu-arch=dav-3510 && ./main
```


```c
#include <cstdint>
#include <iostream>
#include <vector>
#include "c_api/asc_simd.h"
#include "acl/acl.h"

namespace {

constexpr uint32_t INPUT_BYTES = 256;
constexpr uint32_t OUTPUT_BYTES = 256;

__global__ __vector__ void asc_copy_gm2ub_arch_3510_kernel(__gm__ uint8_t* output, __gm__ uint8_t* input)
{
    asc_init();
    __ubuf__ uint8_t local[INPUT_BYTES];
    // Copy INPUT_BYTES from GM to UB, then wait only for PIPE_MTE2.
    asc_copy_gm2ub(local, input, INPUT_BYTES);
    asc_sync_mte2(0);
    asc_copy_ub2gm_align(output, local, INPUT_BYTES);
    asc_sync_mte3(0);
}

void print_data(const char* name, const std::vector<uint8_t>& data)
{
    std::cout << name << ":";
    const uint32_t count = data.size() < 32 ? data.size() : 32;
    for (uint32_t i = 0; i < count; ++i) std::cout << ' ' << +data[i];
    if (data.size() > count) std::cout << " ...";
    std::cout << std::endl;
}
} // namespace

int main()
{
    std::vector<uint8_t> input(INPUT_BYTES), output(OUTPUT_BYTES, 0), golden(OUTPUT_BYTES, 0);
    for (uint32_t i = 0; i < INPUT_BYTES; ++i) input[i] = static_cast<uint8_t>(i + 1);
    for (uint32_t i = 0; i < 256; ++i) golden[i] = input[i];
    aclInit(nullptr);
    aclrtSetDevice(0);
    uint8_t *input_device = nullptr, *output_device = nullptr;
    aclrtMalloc(reinterpret_cast<void**>(&input_device), INPUT_BYTES, ACL_MEM_MALLOC_HUGE_FIRST);
    aclrtMalloc(reinterpret_cast<void**>(&output_device), OUTPUT_BYTES, ACL_MEM_MALLOC_HUGE_FIRST);
    aclrtMemcpy(input_device, INPUT_BYTES, input.data(), INPUT_BYTES, ACL_MEMCPY_HOST_TO_DEVICE);
    aclrtMemcpy(output_device, OUTPUT_BYTES, output.data(), OUTPUT_BYTES, ACL_MEMCPY_HOST_TO_DEVICE);
    asc_copy_gm2ub_arch_3510_kernel<<<1, 0>>>(output_device, input_device);
    aclrtSynchronizeDevice();
    aclrtMemcpy(output.data(), OUTPUT_BYTES, output_device, OUTPUT_BYTES, ACL_MEMCPY_DEVICE_TO_HOST);
    print_data("Input", input);
    print_data("Output", output);
    print_data("Golden", golden);
    const bool passed = output == golden;
    std::cout << (passed ? "[Success] asc_copy_gm2ub passed." : "[Failed] asc_copy_gm2ub failed.") << std::endl;
    aclrtFree(input_device);
    aclrtFree(output_device);
    aclrtResetDevice(0);
    aclFinalize();
    return passed ? 0 : 1;
}
```
