# vector_add M0/M0b 测量 pack

AscendC-IR M0（抽象税）与 M0b（数值一致性）的上板测量打包。CANNBench kernel-only 口径
（cann-bench master `abb6e47`），设备 Ascend 950PR。测量清单（manifest v1.0，2026-09-28 冻结）
见 `docs/evaluation/metrics.md`；计算 lowering 见 ADR 0014。

## 结构

```
vector_add_m0/
├── task/                       # bench root（--task-dir 指向这里）
│   ├── level1/add_m0/          # proto.yaml + golden.py + cases（冻结 shape 16384 f32 单 case）
│   └── metadata/950pr.json     # 显式声明无 baseline（M0 不用 HAP）
└── submissions/
    ├── add_generated/          # 候选1：kernel.asc == examples/vector_add/add_golden.asc（字节一致）
    └── add_reference/          # 候选2：kernel.asc == examples/vector_add/add_reference.asc（字节一致）
```

两个提交均为 cann-bench direct_launch 形态：`build.sh` → cmake（bisheng
`--npu-arch=dav-3510 --asc-aicore-lang` 编内核 TU；无 ASC 标志编译 torch 插件）→
`dist/cann_bench-*.whl`，暴露 `cann_bench.add(x, y) -> Tensor`。

## 构建/运行（在 950PR 容器内，原生 CANN 9.1.0 环境）

前置（一次性，已按 manifest v1.2 配好）：CANN 9.1.0 toolkit + 950-ops（refonly）+ libhccl stub。

```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh

# 单独构建（冒烟）
cd submissions/add_generated && bash build.sh

# 正式评测（cann-bench 根目录；两候选各一次）
./scripts/run_evaluation.sh \
    --source-dir <abs>/pack/vector_add_m0/submissions/add_generated \
    --task-dir  <abs>/pack/vector_add_m0/task \
    --operator Add --device-id 0 --processes-per-card 1 \
    --warmup 3 --repeat 20 --reports-dir <abs>/pack/vector_add_m0/results/add_generated
```

## 冻结项（不得改动）

- 两个 `kernel.asc` 与 `examples/vector_add/add_{golden,reference}.asc` 字节一致（构建前哈希核对）
- 冻结 shape：16384 f32、单核；`build.sh` 拒绝 `--soc != ascend950`
- 判分只读评测归档的原始 `kernel_details.csv`（匹配规则见 manifest）
