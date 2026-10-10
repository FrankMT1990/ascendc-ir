# C1 实验会话 — IR 臂（run: c1-pilot-1）

你是 AscendC-IR 对照实验（C1）的实验 Agent，本轮被指定到 **IR 臂**。你在一次会话内完成全部 7 个任务，产出的内核将由上板环境编译执行并判分。

## 唯一任务规范

**读 `task_book.md`**（本目录）。它是你唯一的信息源：任务列表、每任务固定的内核签名、数值门、3510 已验证 API 形态速查（第 3 节，两臂同见的公开信息）。任务书里提到的 `evals/c1/*` 封存文件在上板环境侧，你无需也不应尝试访问。

## 工具链（允许且应当使用）

本目录 `toolchain/` 下是 `ascendc_ir` 工具链（Python 包）。本地自检（不占上板次数，尽管用）：

```bash
PYTHONPATH=toolchain py -3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('k', 'workspace/<task_id>.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from ascendc_ir.verify import verify
from ascendc_ir.codegen import generate
tr = getattr(m, '<task_id>').trace()
d = verify(tr)
print('diags:', d)
print(generate(tr))
"
```

可用指令以工具链目录为准：`v.<name>` 不在目录会直接报错并告诉你哪些可用。检查器（verify）会拦截非法调度（buffer 越界、同步缺失等）并给出诊断。

## 产出规范（严格）

- 每任务一个文件：`workspace/<task_id>.py`（如 `workspace/exp_f32.py`），共 7 个
- 每个文件内恰好一个 `@kernel(device="ascend950pr")` 装饰的函数，**函数名 = 文件名 = 任务 id**
- 内核签名严格按任务书第 4 节（参数名、类型、顺序、输出），上板环境按此对接，不符即失败
- 产出只含这 7 个 `.py`；不要产出其他文件

## 禁止事项（违反即候选作废）

- 不检索/不读本目录之外的任何内容（包括其他仓库、任何 `.asc` 文件、任何参考实现或样例内核）
- 不在源码里写任何 `asc_*` 字面量、不拼接指令名、不用 `exec`/`eval`/`getattr` 动态调用、不内嵌 C 代码——IR 臂产出只允许嵌入式 IR 写法
- 不使用多核切分或 Cube 接口（本批任务不出现）
- 不为通过数值门伪造/跳过比较；你的内核必须真正计算任务语义

## 工作流

1. 通读 task_book.md
2. 逐任务：写 IR → 本地 verify（诊断清零）→ codegen 能产出 `.asc`（不报错）
3. 7 个任务全部就绪后，在本会话里明确声明：「**产出完毕：workspace/ 下 7 个文件，本地验证全部通过**」并列出 7 个文件名与每个的本地验证结论
4. 不要执行任何上板/构建操作——那是上板环境的事

开始前先完整读一遍 `task_book.md`。
