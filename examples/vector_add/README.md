# vector_add 配对例子

M0（抽象税）配对实验的最小样本。

| 文件 | 角色 |
|---|---|
| `add.py` | AscendC-IR 写法（agent 面） |
| `add_golden.asc` | `codegen.generate(add_custom.trace())` 的已审定输出；`tests/codegen` 做字节级 golden diff |
| `add_reference.asc` | 手写 C API 对照，与 IR 同一调度 |

## 与官方样例的关系

调度结构参照 asc-devkit `examples/02_simd_c_api/00_introduction/01_add/c_api_delicacy_async_add`（固定 commit [`648a6018`](https://gitcode.com/cann/asc-devkit/tree/648a6018207d75af44c6865f96511bafadd90630)）。两处有意偏差：

1. **单核**：官方样例按 `asc_get_block_num()` 做多核切分；AscendC-IR v0.2 还没有 block 词汇（gap，见 `docs/design/vocabulary-evidence.md`）。M0 配对两边同为单核。
2. **x/y 双缓冲**：官方样例是单缓冲全串行；本例用 `stages=2` 流水，检验 WAR 推导。

## 复现

```bash
PYTHONPATH=src python examples/vector_add/add.py        # 打印 canonical JSON
PYTHONPATH=src python -c "from examples.vector_add.add import add_custom; from ascendc_ir.codegen import generate; print(generate(add_custom.trace()))"
```
