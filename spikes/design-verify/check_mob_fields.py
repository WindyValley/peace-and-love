"""
实测 Mob.goalSelector / targetSelector 的访问修饰符
====================================================
T-NEUT-001 需要访问这两个字段做 Goal 移除。
- 若 public：直接访问
- 若 protected/final：需 Accessor Mixin 或 AccessWidener

P1 只验证了 Merchant 接口注入不需 AT，没覆盖字段访问。这里补验。
"""
import io
import zipfile
import struct
from pathlib import Path

# 定位 named jar（Loom 反混淆产物，含 Mob.class 真实类名）
# 在项目 .gradle/loom-cache/minecraftMaven 下（构建时 Loom 生成）
ROOT = Path(__file__).resolve().parent.parent.parent
LOOM = ROOT / ".gradle/loom-cache/minecraftMaven/net/minecraft"
CANDIDATES = sorted(LOOM.rglob("minecraft-merged-*-v2.jar")) + \
             sorted(LOOM.rglob("*-neoforge-21.1.250.jar"))
CANDIDATES = [p for p in CANDIDATES if "sources" not in p.name]
JAR = next((p for p in CANDIDATES if p.exists()), None)

print("jar:", JAR, "存在:", JAR and JAR.exists())


def parse_fields(data: bytes):
    """解析 class 文件的字段名 + access_flags"""
    br = io.BytesIO(data)
    u1 = lambda: struct.unpack(">B", br.read(1))[0]
    u2 = lambda: struct.unpack(">H", br.read(2))[0]
    u4 = lambda: struct.unpack(">I", br.read(4))[0]

    magic = u4()
    assert magic == 0xCAFEBABE
    br.read(4)  # minor, major
    cp_count = u2()
    cp = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = u1()
        if tag == 1:  # Utf8
            ln = u2()
            cp[i] = ("Utf8", br.read(ln).decode("utf-8", "replace"))
        elif tag in (7, 8, 16, 19, 20):
            br.read(2)
        elif tag in (15,):
            br.read(3)
        elif tag in (9, 10, 11, 12, 17, 18):
            br.read(4)
        elif tag in (5, 6):
            br.read(8)
            i += 1
        else:
            br.read(4)
        i += 1

    def utf(idx):
        e = cp[idx]
        return e[1] if e and e[0] == "Utf8" else "?"

    br.read(6)  # access, this, super
    for _ in range(u2()):  # interfaces
        br.read(2)

    fields = []
    fc = u2()
    for _ in range(fc):
        acc = u2()
        name = utf(u2())
        desc = utf(u2())
        ac = u2()
        for _ in range(ac):
            br.read(2)
            ln = u4()
            br.read(ln)
        fields.append((name, desc, acc))
    return fields


FLAGS = {0x0001: "public", 0x0002: "private", 0x0004: "protected",
         0x0010: "final", 0x0008: "static", 0x0040: "volatile"}

if JAR and JAR.exists():
    with zipfile.ZipFile(JAR) as z:
        # 混淆后的 Mob 类名未知，先找 Named 版（loom 产物），或直接读混淆类
        # 这里读 named 版更直观：从 neoforge 的 loom 缓存
        names = [n for n in z.namelist() if n == "net/minecraft/world/entity/Mob.class"]
        print("Mob.class 候选:", names[:5])
        if not names:
            print("⚠️ 未找到 net/minecraft/world/entity/Mob.class")
        else:
            data = z.read(names[0])
            for name, desc, acc in parse_fields(data):
                if "goalSelector" in name or "targetSelector" in name or "GoalSelector" in desc:
                    mods = " ".join(v for k, v in FLAGS.items() if acc & k)
                    print(f"  {name:20s} {desc:40s} [{mods}]")
            # 顺带查 brain 字段
            print("  --- 全部 Goal/Brain 相关字段 ---")
            for name, desc, acc in parse_fields(data):
                if "goal" in name.lower() or "brain" in name.lower():
                    mods = " ".join(v for k, v in FLAGS.items() if acc & k)
                    print(f"  {name:20s} {desc:45s} [{mods}]")
else:
    print("⚠️ 找不到 server jar")
