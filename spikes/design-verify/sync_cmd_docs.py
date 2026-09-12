"""更新 T-CFG-003 / T-CFG-004 任务卡：命令名与设计文档对齐为 /pal"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def patch_task(name: str, replacements: list[tuple[str, str]]):
    f = ROOT / "docs" / "tasks" / f"{name}.md"
    txt = f.read_text(encoding="utf-8-sig")
    for old, new in replacements:
        if old not in txt:
            print(f"  ⚠️ {name} 未找到: {old[:50]}")
            continue
        txt = txt.replace(old, new)
    f.write_text(txt, encoding="utf-8", newline="\n")
    print(f"  ✅ {name}")


# T-CFG-003: /peaceandlove reload -> /pal reload
patch_task("T-CFG-003", [
    ("# T-CFG-003: /peaceandlove reload 热重载命令",
     "# T-CFG-003: /pal reload 热重载命令"),
    ("`/peaceandlove reload` 需 OP 权限（level 2）",
     "`/pal reload` 需 OP 权限（level 2），`/peaceandlove` 作为别名同时注册"),
])

# T-CFG-004: /peaceandlove whitelist -> /pal whitelist
patch_task("T-CFG-004", [
    ("# T-CFG-004: /peaceandlove whitelist 命令族",
     "# T-CFG-004: /pal whitelist 命令族"),
])

print("\n完成。设计文档 docs/02-design.md §7 已先行更新。")
