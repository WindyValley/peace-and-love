"""读取探针日志的 P1/P3 输出段（避开 MSYS 中文乱码）"""
from pathlib import Path

log = Path(__file__).resolve().parent / "neoforge_run2.log"
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()

start = None
for i, l in enumerate(lines):
    if "Peace And Love" in l and "探针" in l:
        start = max(0, i - 2)
        break

if start is None:
    for i, l in enumerate(lines):
        if "P1" in l and "Mixin" in l:
            start = max(0, i - 4)
            break

if start is None:
    print("未找到探针输出段")
else:
    for l in lines[start:start + 24]:
        print(l)
