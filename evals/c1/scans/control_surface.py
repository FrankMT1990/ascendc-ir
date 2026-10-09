"""C1 对照臂越面扫描。

扫描提交的全部源文件与 pack 启动配置（.py/.asc/.cpp/.h/.txt/.cmake/.json/.sh），
对每个 asc_* 记号对照允许面（allowed_surface.json）：
  - 允许清单内 → 通过
  - Cube 接口 → 越面（cube）
  - 多核切分词汇 → 越面（multicore）
  - 其余 asc_* → 越面（offlist）

命中越面的候选不进 M1/M2/M3。退出码 0 = 干净；1 = 命中。
"""

import json
import re
import sys
from pathlib import Path

RE_ASC = re.compile(r"\basc_[a-z0-9_]+")
RE_NONASC_MULTI = re.compile(r"\b(get_block_id|block_idx|block_num)\b")

SCAN_EXTS = {".py", ".asc", ".cpp", ".h", ".hpp", ".txt", ".cmake", ".json", ".sh", ".yaml", ".yml"}


def load_surface(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    allowed = set(d["allowed_asc_tokens"])
    cube = set(d["forbidden_cube_tokens"])
    multi = set(d["forbidden_multicore_tokens"])
    multi_re = {t for t in multi if not t.startswith("asc_")}
    return allowed, cube, multi_re


def scan_file(path: Path, allowed, cube, multi_re) -> list:
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [f"unreadable: {path}"]
    for ln, line in enumerate(text.splitlines(), 1):
        tag = f"{path}:{ln}"
        for m in RE_ASC.finditer(line):
            tok = m.group(0)
            if tok in allowed:
                continue
            kind = "cube" if tok in cube else "offlist"
            hits.append(f"{tag} {kind}: {tok}")
        for m in RE_NONASC_MULTI.finditer(line):
            hits.append(f"{tag} multicore: {m.group(0)}")
    return hits


def main(argv):
    here = Path(__file__).resolve().parent
    allowed, cube, multi_re = load_surface(here / "allowed_surface.json")
    targets = []
    for a in argv[1:]:
        p = Path(a)
        if p.is_dir():
            targets.extend(q for q in sorted(p.rglob("*")) if q.is_file() and q.suffix in SCAN_EXTS)
        elif p.is_file():
            targets.append(p)
    all_hits = []
    for t in targets:
        all_hits.extend(scan_file(t, allowed, cube, multi_re))
    for h in all_hits:
        print(h)
    print(f"control_surface: {len(targets)} files scanned, {len(all_hits)} hits")
    return 1 if all_hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
