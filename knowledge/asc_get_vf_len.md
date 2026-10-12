---
type: API
title: asc_get_vf_len
description: 获取Tensor位宽VL（Vector Length）的大小。
tags:
- task.lookup
- topic.implementation.api_layer.c_api
status: stable
sources:
- resource: cann-docs-raw/asc-devkit/docs/zh/api/SIMD-API/c_api/utils/sys_var/asc_get_vf_len.md
  role: primary
created_at: '2026-09-03T08:52:46Z'
updated_at: '2026-10-10T04:14:14Z'
platforms:
- '950'
source_headers:
- include/c_api/utils/sys_var.h
- include/c_api/asc_simd.h
---

# asc_get_vf_len

## 功能说明

头文件路径为：`"c_api/utils/sys_var.h"`。

获取当前芯片的矢量寄存器位宽VL（[Vector Length](../../defs/type/data_type_definition.md)），即矢量计算单元单次Repeat可处理的元素个数。VL是Reg矢量计算循环每轮消耗的元素数量，常用于推导mask长度、循环次数、单次搬运元素数等参数。本接口在AIC与AIV上均可调用，返回值含义一致。

## 函数原型

```c
__aicore__ inline constexpr int64_t asc_get_vf_len()
```

## 参数说明

无

## 返回值说明

位宽VL（Vector Length）的大小。

## 流水类型

PIPE_S

## 约束说明

- 本接口不触发硬件指令，不依赖任何特殊寄存器或前置setter接口配置，可在AIC与AIV上下文中调用。
- 返回值反映当前芯片的矢量寄存器位宽，同一kernel内多次调用返回值相同。
- 本接口不支持纯SIMT编译模式，在该模式下包含对应头文件会触发编译错误。

## 调用示例

将代码保存为`example.asc`后，可通过`bisheng`命令编译运行，其中`--npu-arch`参数需根据实际产品型号指定对应的NPU架构，具体产品与NPU架构的映射关系请参考[\_\_NPU\_ARCH\_\_](../../../../../guides/programming_guide/language_extension/simd_builtin_keywords.md#npu-arch)。


以Ascend 950PR/Ascend 950DT产品（对应NPU架构为`dav-3510`）为例，编译运行命令如下：

```bash
bisheng example.asc -o main --npu-arch=dav-3510 && ./main
```


```cpp
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <vector>
#include "c_api/asc_simd.h"
#include "acl/acl.h"

namespace {
constexpr uint32_t ELEMENTS = 16;
constexpr uint32_t BYTES = ELEMENTS * sizeof(uint64_t);

void print_data(const char* label, const std::vector<uint64_t>& data)
{
    std::cout << label << ":";
    for (uint32_t i = 0; i < 8; ++i) std::cout << ' ' << data[i];
    std::cout << " ..." << std::endl;
}

void print_hex(const char* label, const std::vector<uint64_t>& data)
{
    std::cout << label << ":" << std::hex;
    for (uint32_t i = 0; i < 4; ++i) std::cout << " 0x" << data[i];
    std::cout << std::dec << std::endl;
}

__global__ __vector__ void asc_get_vf_len_kernel(__gm__ uint64_t* output)
{
    asc_init();
    constexpr uint64_t vf_bytes = asc_get_vf_len();
    output[0] = vf_bytes;
    output[1] = vf_bytes / sizeof(float);
    asc_dcci_single(output);
}

} // namespace

int main()
{
    std::vector<uint64_t> output(ELEMENTS, ~0ULL);
    aclInit(nullptr);
    aclrtSetDevice(0);
    uint64_t* output_device = nullptr;
    aclrtMalloc(reinterpret_cast<void**>(&output_device), BYTES, ACL_MEM_MALLOC_HUGE_FIRST);
    aclrtMemcpy(output_device, BYTES, output.data(), BYTES, ACL_MEMCPY_HOST_TO_DEVICE);
    asc_get_vf_len_kernel<<<1, 0>>>(output_device);
    aclrtSynchronizeDevice();
    aclrtMemcpy(output.data(), BYTES, output_device, BYTES, ACL_MEMCPY_DEVICE_TO_HOST);
    print_data("Observed", output);
    print_hex("Observed hex", output);
    const bool passed = output[0] == 256 && output[1] == 64;
    std::cout << (passed ? "[Success] asc_get_vf_len passed." : "[Failed] asc_get_vf_len failed.") << std::endl;
    aclrtFree(output_device);
    aclrtResetDevice(0);
    aclFinalize();
    return passed ? 0 : 1;
}
```

## 配套 API 与常见组合

- [asc_storealign](../../reg_compute/store/asc_storealign.md)——storealign 卡明示单次搬出量为 VL(256字节)，循环步长与掩码元素数须由 asc_get_vf_len() 推导，参数派生依赖成立
- [asc_loadalign](../../reg_compute/load/asc_loadalign.md)——loadalign 单次搬入 VL 字节，每轮元素数与地址步长由 asc_get_vf_len() 推导，get_vf_len 卡明示 VL 用于推导矢量循环每轮消耗
- [asc_update_mask](../../reg_compute/reg_mask/asc_update_mask.md)——update_mask每轮减去的元素数即get_vf_len()/sizeof(dtype)，位宽模式须与dtype一致共同构成VL尾块循环，vf_len卡自述"常用于推导mask长度"
