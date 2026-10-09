"""C1 IR 臂逃逸扫描（M7）。

扫描提交的 .py 及其写出的所有文件，检测逃逸手法：
  1. 字面 asc_* 记号（含出现在字符串里的）
  2. exec/eval
  3. 动态/拼接的指令名（getattr 动态调用、v.compute 的参数不是字符串字面量）
  4. 另写 .asc 文件再在 IR 里调用（打开/引用 .asc 路径）
  5. 内嵌 C 字符串（字符串里含 __ubuf__/__gm__/#include/extern "C"）

退出码 0 = 干净；1 = 命中（违规候选，不进 M1/M2/M3）。
"""

import re
import sys
from pathlib import Path

RE_ASC = re.compile(r"\basc_[a-z0-9_]+")
RE_EXEC_EVAL = re.compile(r"\b(exec|eval)\s*\(")
RE_GETATTR = re.compile(r"\bgetattr\s*\(")
RE_COMPUTE_NONLIT = re.compile(r"\.compute\s*\(\s*[^\"'\n]")
RE_COMPUTE_CONCAT = re.compile(r"\.compute\s*\(\s*[\"'][^\"']*[\"']\s*\+")
RE_ASC_FILE = re.compile(r"['\"][^'\"]*\.asc['\"]")
RE_C_STRING = re.compile(r"[\"'][^\"']*(__ubuf__|__gm__|#include|extern \"C\")")

C_EXTS = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".cfg", ".toml"}


def scan_file(path: Path) -> list:
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [f"unreadable: {path}"]
    for ln, line in enumerate(text.splitlines(), 1):
        tag = f"{path}:{ln}"
        if RE_ASC.search(line):
            hits.append(f"{tag} literal asc_*: {RE_ASC.search(line).group(0)}")
        if RE_EXEC_EVAL.search(line):
            hits.append(f"{tag} exec/eval call")
        if RE_GETATTR.search(line):
            hits.append(f"{tag} getattr dynamic call")
        if RE_COMPUTE_NONLIT.search(line) or RE_COMPUTE_CONCAT.search(line):
            hits.append(f"{tag} v.compute with non-literal/concatenated name")
        if RE_ASC_FILE.search(line):
            hits.append(f"{tag} references .asc file")
        if RE_C_STRING.search(line):
            hits.append(f"{tag} embedded C string")
    return hits


def main(argv):
    targets = []
    for a in argv[1:]:
        p = Path(a)
        if p.is_dir():
            targets.extend(q for q in sorted(p.rglob("*")) if q.is_file() and q.suffix in C_EXTS)
        elif p.is_file():
            targets.append(p)
    all_hits = []
    for t in targets:
        all_hits.extend(scan_file(t))
    for h in all_hits:
        print(h)
    print(f"ir_escape: {len(targets)} files scanned, {len(all_hits)} hits")
    return 1 if all_hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
