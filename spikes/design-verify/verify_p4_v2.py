"""
P4 v2 —— 沿继承链查 NeutralMob，并找出真正实现它的生物
=========================================================
v1 只查了直接接口列表，可能漏掉从父类继承的情况
（如 Piglin extends AbstractPiglin，NeutralMob 可能在 AbstractPiglin 上）。

v2：
  1. 沿继承链递归查找 NeutralMob
  2. 反向扫描：全 jar 找出所有实现 NeutralMob 的实体类
  3. 对照本模组的 38 个已适配生物，找出真正有交集的
"""
import io
import re
import struct
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
JAR = BASE.parent / "r3-ai" / "server-1.21.1.jar"
MAPPINGS = BASE.parent / "r3-ai" / "server_mappings.txt"

exec((BASE / "extract_api.py").read_text(encoding="utf-8").split(
    "def main():")[0].split('"""', 2)[2])

NEUTRAL_MOB = "net.minecraft.world.entity.NeutralMob"


def main():
    n2o, o2n, members = load_mappings()
    zf = open_mc_jar(JAR)
    names = set(zf.namelist())
    nm_obf = n2o.get(NEUTRAL_MOB)
    nm_entry = nm_obf.replace(".", "/")

    print("=" * 78)
    print("P4 v2 —— NeutralMob 继承链与全量扫描")
    print("=" * 78)
    print(f"\nNeutralMob 混淆名：{nm_obf}")

    # 缓存已解析的类
    cache = {}

    def load(obf_internal):
        """obf_internal 形如 'bts'（内部名，斜杠形式）"""
        if obf_internal in cache:
            return cache[obf_internal]
        entry = f"{obf_internal}.class"
        if entry not in names:
            cache[obf_internal] = None
            return None
        info = parse_class(zf.read(entry))
        cache[obf_internal] = info
        return info

    def implements_nm(obf_internal, depth=0, chain=None):
        """沿继承链 + 接口树递归查 NeutralMob"""
        if chain is None:
            chain = []
        if depth > 12 or obf_internal is None:
            return None
        if obf_internal == nm_entry:
            return chain
        info = load(obf_internal)
        if not info:
            return None
        # 直接接口
        for ifc in info["ifaces"]:
            if ifc == nm_entry:
                return chain + [obf_internal]
            r = implements_nm(ifc, depth + 1, chain + [obf_internal])
            if r:
                return r
        # 父类
        if info["super"]:
            return implements_nm(info["super"], depth + 1, chain + [obf_internal])
        return None

    # ── 1. 检查本模组关心的 6 个 Brain 系生物 ──
    TARGETS = {
        "net.minecraft.world.entity.monster.piglin.Piglin": "猪灵",
        "net.minecraft.world.entity.monster.piglin.PiglinBrute": "猪灵蛮兵",
        "net.minecraft.world.entity.monster.piglin.AbstractPiglin": "猪灵基类",
        "net.minecraft.world.entity.monster.hoglin.Hoglin": "疣猪兽",
        "net.minecraft.world.entity.monster.Zoglin": "僵尸疣猪兽",
        "net.minecraft.world.entity.monster.warden.Warden": "监守者",
        "net.minecraft.world.entity.monster.breeze.Breeze": "旋风人",
    }

    print("\n" + "=" * 78)
    print("① Brain 系 6 生物 —— 沿继承链检查")
    print("=" * 78)
    for fq, zh in TARGETS.items():
        obf = n2o.get(fq)
        if not obf:
            print(f"  {zh:<10} ❌ mappings 找不到")
            continue
        internal = obf.replace(".", "/")
        chain = implements_nm(internal)
        if chain:
            readable = [o2n.get(c.replace("/", "."), c).split(".")[-1] for c in chain]
            print(f"  {zh:<10} ✅ 实现 NeutralMob，路径：{' → '.join(readable)}")
        else:
            info = load(internal)
            sup = "—"
            if info and info["super"]:
                sup = o2n.get(info["super"].replace("/", "."), info["super"]).split(".")[-1]
            print(f"  {zh:<10} ❌ 未实现（父类 {sup}）")

    # ── 2. 全量反扫：谁真正实现了 NeutralMob ──
    print("\n" + "=" * 78)
    print("② 全量扫描 —— 原版中所有实现 NeutralMob 的实体")
    print("=" * 78)
    found = []
    for entry in names:
        if not entry.endswith(".class"):
            continue
        internal = entry[:-6]
        info = load(internal)
        if not info:
            continue
        if nm_entry in info["ifaces"]:
            real = o2n.get(internal.replace("/", "."), internal)
            found.append(real)

    print(f"\n  直接实现 NeutralMob 的类（{len(found)} 个）：")
    for f in sorted(found):
        print(f"      {f}")

    # ── 3. 与本模组 38 个已适配生物求交集 ──
    print("\n" + "=" * 78)
    print("③ 与本模组 38 个已适配生物的交集")
    print("=" * 78)
    import json
    plan = json.loads((BASE.parent / "r3-ai" / "neutralization_plan_v3.json")
                      .read_text(encoding="utf-8"))
    adapted_ids = set()
    for m in plan["goal_system"] + plan["brain_system"]:
        if m["id"] != "ender_dragon":
            adapted_ids.add(m["id"])

    # 用类名末段粗匹配 entity id
    def cls_to_id(fq):
        n = fq.split(".")[-1]
        s = re.sub(r"(?<!^)(?=[A-Z])", "_", n).lower()
        return s

    inter = []
    for f in found:
        cid = cls_to_id(f)
        if cid in adapted_ids:
            inter.append((cid, f))

    if inter:
        print(f"\n  ⚠️ 交集 {len(inter)} 个 —— 这些生物需检查冲突：")
        for cid, f in sorted(inter):
            print(f"      {cid:<24} {f}")
    else:
        print("\n  ✅ 无交集 —— 本模组的 38 个已适配生物中，")
        print("     没有任何一个原版实现了 NeutralMob")

    print("\n  （参考）实现 NeutralMob 但不在适配列表的：")
    for f in sorted(found):
        cid = cls_to_id(f)
        if cid not in adapted_ids:
            print(f"      {cid:<24} {f.split('.')[-1]}")

    print("\n" + "=" * 78)
    print("完成")
    print("=" * 78)


main()
