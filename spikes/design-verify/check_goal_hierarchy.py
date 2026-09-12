"""
实测中立化相关 Goal 类的继承链（named jar）
==============================================
GoalBasedStrategy 的谓词要精确：
- 移除：MeleeAttackGoal、RangedXxx、NearestAttackableTargetGoal、
        及 TargetGoal 中非 HurtByTargetGoal 者
- 保留：HurtByTargetGoal（受击反击由 ANGER 接管）

风险：谓词 `goal instanceof TargetGoal && !(goal instanceof HurtByTargetGoal)`
若存在「HurtByTargetGoal 的子类」会被误保留——这恰是我们要的（保留反击）。
但要确认没有别的「必须保留」的 TargetGoal 子类被误移除。
"""
import io
import zipfile
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LOOM = ROOT / ".gradle/loom-cache/minecraftMaven/net/minecraft"
JARS = [p for p in LOOM.rglob("minecraft-merged-*-v2.jar") if "sources" not in p.name]
JAR = JARS[0]
print("jar:", JAR.name)

GOAL_PKG = "net/minecraft/world/entity/ai/goal/"
TARGET_PKG = GOAL_PKG + "target/"
# (simpleName, package) —— TargetGoal 系在 goal/target 子包
TARGETS = [
    ("Goal", GOAL_PKG),
    ("MeleeAttackGoal", GOAL_PKG),
    ("RangedAttackGoal", GOAL_PKG),
    ("RangedBowAttackGoal", GOAL_PKG),
    ("RangedCrossbowAttackGoal", GOAL_PKG),
    ("TargetGoal", TARGET_PKG),
    ("NearestAttackableTargetGoal", TARGET_PKG),
    ("HurtByTargetGoal", TARGET_PKG),
    # 常见 TargetGoal 子类，查是否会被误移除
    ("DefendVillageTargetGoal", TARGET_PKG),
    ("ResetUniversalAngerTargetGoal", TARGET_PKG),
    ("NonTameRandomTargetGoal", TARGET_PKG),
    ("OwnerHurtTargetGoal", TARGET_PKG),
    ("OwnerHurtByTargetGoal", TARGET_PKG),
]


def super_of(data: bytes):
    br = io.BytesIO(data)
    u1 = lambda: struct.unpack(">B", br.read(1))[0]
    u2 = lambda: struct.unpack(">H", br.read(2))[0]
    u4 = lambda: struct.unpack(">I", br.read(4))[0]
    assert u4() == 0xCAFEBABE
    br.read(4)
    cp_count = u2()
    cp = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = u1()
        if tag == 1:
            ln = u2()
            cp[i] = ("Utf8", br.read(ln).decode("utf-8", "replace"))
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = ("Class", u2()) if tag == 7 else None
            if tag != 7:
                br.read(2)
        elif tag == 15:
            br.read(3)
        elif tag in (9, 10, 11, 12, 17, 18):
            br.read(4)
        elif tag in (5, 6):
            br.read(8)
            i += 1
        else:
            br.read(4)
        i += 1

    def cls_name(idx):
        e = cp[idx]
        if e and e[0] == "Class":
            u = cp[e[1]]
            return u[1] if u and u[0] == "Utf8" else "?"
        return "?"

    br.read(2)  # access
    this_idx = u2()
    super_idx = u2()
    return cls_name(this_idx), cls_name(super_idx)


with zipfile.ZipFile(JAR) as z:
    for simple, pkg in TARGETS:
        path = pkg + simple + ".class"
        try:
            data = z.read(path)
            this_c, super_c = super_of(data)
            print(f"  {simple:32s} extends {super_c.split('/')[-1]}")
        except KeyError:
            print(f"  {simple:32s} <未找到 {path}>")
