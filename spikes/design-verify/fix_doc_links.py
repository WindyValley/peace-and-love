"""
修复文档移入 docs/ 后失效的相对路径引用
=========================================
移动前 → 移动后：
    02-adr/xxx.md      → docs/adr/xxx.md
    03-tasks/xxx.md    → docs/tasks/xxx.md
    01-requirements.md → docs/01-requirements.md

docs/ 内部文档互相引用时用相对路径（同级直接写文件名），
README.md 在根目录，引用要带 docs/ 前缀。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DOCS = ROOT / "docs"

# docs/ 下同级文档之间的引用：02-adr/ → adr/，03-tasks/ → tasks/
RULES_IN_DOCS = [
    (r"`02-adr/", "`adr/"),
    (r"`03-tasks/", "`tasks/"),
    (r"\(02-adr/", "(adr/"),
    (r"\(03-tasks/", "(tasks/"),
    (r"02-adr/(\d{3}-[\w-]+\.md)", r"adr/\1"),
    (r"03-tasks/(T-[\w-]+\.md)", r"tasks/\1"),
]

# docs/adr/ 和 docs/tasks/ 下的文档，引用 docs/ 根层文档要加 ../
RULES_IN_SUBDIR = [
    (r"`(0[123]-[\w-]+\.md)`", r"`../\1`"),
    (r"`(RISKS\.md)`", r"`../\1`"),
    (r"`(P1-P4-VERIFY\.md)`", r"`../\1`"),
    (r"`(SPIKE-REPORT\.md)`", r"`../\1`"),
    (r"`(PROJECT_STATUS\.md)`", r"`../\1`"),
    (r"`02-adr/(\d{3}-[\w-]+)`", r"`../adr/\1`"),
    (r"`02-adr/", "`../adr/"),
]

changed = []

# 1. docs/ 根层文档
for f in sorted(DOCS.glob("*.md")):
    txt = orig = f.read_text(encoding="utf-8")
    for pat, rep in RULES_IN_DOCS:
        txt = re.sub(pat, rep, txt)
    if txt != orig:
        f.write_text(txt, encoding="utf-8")
        changed.append(f"docs/{f.name}")

# 2. docs/adr/ 与 docs/tasks/ 子目录文档
for sub in ("adr", "tasks"):
    for f in sorted((DOCS / sub).glob("*.md")):
        txt = orig = f.read_text(encoding="utf-8")
        for pat, rep in RULES_IN_SUBDIR:
            txt = re.sub(pat, rep, txt)
        # 避免重复加 ../
        txt = txt.replace("../../", "../")
        if txt != orig:
            f.write_text(txt, encoding="utf-8")
            changed.append(f"docs/{sub}/{f.name}")

print(f"修改了 {len(changed)} 个文件")
for c in changed[:25]:
    print(f"  {c}")
if len(changed) > 25:
    print(f"  ... 及其余 {len(changed)-25} 个")

# 校验：列出仍然指向旧路径的引用
print("\n=== 残留的旧路径引用 ===")
bad = 0
for f in list(DOCS.rglob("*.md")) + [ROOT / "README.md"]:
    txt = f.read_text(encoding="utf-8")
    for m in re.finditer(r"`?(0[23]-(?:adr|tasks)/[^\s`)]+)", txt):
        print(f"  {f.relative_to(ROOT)}: {m.group(1)}")
        bad += 1
print(f"共 {bad} 处" if bad else "  无")
