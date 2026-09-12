"""
R3 spike — 判定 1.21.1 每个敌对生物用的是 Goal 系统还是 Brain 系统
====================================================================

方法（不靠猜，用官方 mappings + 反编译字节码验证）：
  1. 从 server.txt (Mojang 官方 mappings) 解析出所有 Mob 子类的混淆名映射
  2. 从 server.jar 中读取每个实体类的字节码，检查它是否：
       • 覆写 registerGoals()          → Goal 系统
       • 覆写 makeBrain() / brainProvider() → Brain 系统
  3. 交叉验证：检查类的父类链（PathfinderMob / Monster / Raider ...）

依赖：仅标准库（zipfile 读 jar，手工解析 class 常量池找方法名）
"""

import json
import os
import re
import struct
import sys
import urllib.request
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
SERVER_JAR = os.path.join(BASE, "server-1.21.1.jar")
MAPPINGS = os.path.join(BASE, "server_mappings.txt")
SERVER_URL = "https://piston-data.mojang.com/v1/objects/59353fb40c36d304f2035d51e7d6e6baa98dc05c/server.jar"

# 1.21.1 全部会主动攻击玩家的生物（含中立但会反击的），用官方类名
HOSTILE_ENTITIES = [
    # ── 经典 Goal 系统敌对生物 ──
    "Zombie", "ZombieVillager", "Husk", "Drowned", "ZombifiedPiglin",
    "Skeleton", "WitherSkeleton", "Stray", "Bogged",
    "Creeper", "Spider", "CaveSpider", "Silverfish", "Endermite",
    "EnderMan", "Witch", "Slime", "MagmaCube", "Blaze", "Ghast",
    "Guardian", "ElderGuardian", "Shulker", "Phantom", "Vex",
    "Pillager", "Vindicator", "Evoker", "Illusioner", "Ravager",
    "Giant", "IronGolem", "SnowGolem", "Wolf", "PolarBear",
    "Llama", "TraderLlama", "Panda", "Bee", "Dolphin", "Rabbit",
    "Goat", "Turtle", "Armadillo", "Camel", "Frog",
    # ── Brain 系统（怀疑）──
    "Piglin", "PiglinBrute", "Hoglin", "Zoglin", "Warden", "Breeze",
    "Axolotl", "Allay", "Villager", "Sniffer", "Tadpole",
    # ── Boss ──
    "EnderDragon", "WitherBoss",
]

# 关键方法名（Mojang 官方名）
GOAL_METHODS = ["registerGoals", "addBehaviourGoals", "registerTargetGoals"]
BRAIN_METHODS = ["makeBrain", "brainProvider", "getBrain", "customServerAiStep"]


def parse_mappings(path):
    """
    解析 Mojang ProGuard mappings。格式：
      net.minecraft.world.entity.monster.Zombie -> bcs:
          123:456:void registerGoals() -> m
    返回 {官方类名: (混淆类名, {官方方法名: 混淆方法名})}
    """
    result = {}
    cur_class = None
    cur_methods = {}
    cur_obf = None

    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" ") and not line.startswith("\t"):
                # 类行
                if cur_class:
                    result[cur_class] = (cur_obf, cur_methods)
                m = re.match(r"^(\S+)\s*->\s*(\S+):", line.strip())
                if m:
                    full, obf = m.group(1), m.group(2)
                    cur_class = full
                    cur_obf = obf
                    cur_methods = {}
                else:
                    cur_class = None
            else:
                # 成员行
                if cur_class is None:
                    continue
                s = line.strip()
                mm = re.match(r"^(?:\d+:\d+:)?\S+\s+(\w+)\([^)]*\)\s*->\s*(\S+)$", s)
                if mm:
                    cur_methods[mm.group(1)] = mm.group(2)
        if cur_class:
            result[cur_class] = (cur_obf, cur_methods)
    return result


def class_strings(jar, obf_name):
    """
    从 jar 中读取 obf_name.class，解析常量池，返回所有 UTF8 字符串集合。
    用于判断该类引用了哪些方法名/类名。
    """
    try:
        data = jar.read(obf_name.replace(".", "/") + ".class")
    except KeyError:
        return None
    if data[:4] != b"\xca\xfe\xba\xbe":
        return None
    pos = 8
    count = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    strings = set()
    i = 1
    while i < count:
        tag = data[pos]
        pos += 1
        if tag == 1:  # UTF8
            ln = struct.unpack(">H", data[pos:pos + 2])[0]
            pos += 2
            try:
                strings.add(data[pos:pos + ln].decode("utf-8", "replace"))
            except Exception:
                pass
            pos += ln
        elif tag in (7, 8, 16, 19, 20):
            pos += 2
        elif tag in (15,):
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            i += 1  # long/double 占两个槽
        else:
            break
        i += 1
    return strings


def declared_methods(jar, obf_name):
    """解析 class 文件的 methods 表，返回本类**声明**的方法混淆名集合"""
    try:
        data = jar.read(obf_name.replace(".", "/") + ".class")
    except KeyError:
        return None, None
    if data[:4] != b"\xca\xfe\xba\xbe":
        return None, None

    pos = 8
    cp_count = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    cp = {}
    i = 1
    while i < cp_count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            ln = struct.unpack(">H", data[pos:pos + 2])[0]
            pos += 2
            cp[i] = data[pos:pos + ln].decode("utf-8", "replace")
            pos += ln
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = struct.unpack(">H", data[pos:pos + 2])[0]
            pos += 2
        elif tag == 15:
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            i += 1
        else:
            return None, None
        i += 1

    # access_flags(2) this_class(2) super_class(2)
    pos += 2
    this_idx = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    super_idx = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    super_name = cp.get(cp.get(super_idx)) if super_idx else None

    # interfaces
    ic = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2 + ic * 2

    # fields
    fc = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    for _ in range(fc):
        pos += 6
        ac = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        for _ in range(ac):
            pos += 2
            alen = struct.unpack(">I", data[pos:pos + 4])[0]
            pos += 4 + alen

    # methods
    mc = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    methods = set()
    for _ in range(mc):
        pos += 2  # access
        nidx = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        pos += 2  # descriptor
        methods.add(cp.get(nidx))
        ac = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        for _ in range(ac):
            pos += 2
            alen = struct.unpack(">I", data[pos:pos + 4])[0]
            pos += 4 + alen

    return methods, super_name


def main():
    if not os.path.exists(MAPPINGS):
        print("!! 缺少 server_mappings.txt")
        sys.exit(1)

    if not os.path.exists(SERVER_JAR):
        print("[*] 下载 server.jar (51 MB) ...", flush=True)
        urllib.request.urlretrieve(SERVER_URL, SERVER_JAR)
    print("[*] server.jar:", os.path.getsize(SERVER_JAR), "bytes")

    print("[*] 解析官方 mappings ...", flush=True)
    maps = parse_mappings(MAPPINGS)
    print("[*] 映射类数:", len(maps))

    # 建立 简单类名 → 全限定名 索引（只取 net.minecraft.world.entity.*）
    simple = {}
    for full in maps:
        if full.startswith("net.minecraft.world.entity") or full.startswith("net.minecraft.world.boss"):
            simple.setdefault(full.rsplit(".", 1)[-1], full)

    # server.jar 内 MC 类在 versions/1.21.1/server-1.21.1.jar 中（bundler 结构）
    with zipfile.ZipFile(SERVER_JAR) as z:
        names = z.namelist()
        inner = [n for n in names if n.endswith(".jar") and "server" in n]
        if inner:
            print("[*] bundler 结构，内层 jar:", inner[:3])
            import io
            with z.open(inner[0]) as f:
                inner_bytes = f.read()
            jar = zipfile.ZipFile(io.BytesIO(inner_bytes))
        else:
            jar = z

        results = []
        for ent in HOSTILE_ENTITIES:
            full = simple.get(ent)
            if not full:
                results.append((ent, "?", "映射未找到", "", ""))
                continue
            obf, mm = maps[full]

            declared, super_obf = declared_methods(jar, obf)
            if declared is None:
                results.append((ent, obf, "class 读取失败", "", ""))
                continue

            # 判定：本类是否声明了 registerGoals / makeBrain 的混淆名
            goal_hits = []
            brain_hits = []
            for om in GOAL_METHODS:
                if om in mm and mm[om] in declared:
                    goal_hits.append(om)
            for om in BRAIN_METHODS:
                if om in mm and mm[om] in declared:
                    brain_hits.append(om)

            # 父类官方名
            super_full = None
            for f2, (o2, _) in maps.items():
                if o2 == super_obf:
                    super_full = f2.rsplit(".", 1)[-1]
                    break

            if brain_hits and not goal_hits:
                verdict = "BRAIN"
            elif goal_hits and not brain_hits:
                verdict = "GOAL"
            elif goal_hits and brain_hits:
                verdict = "MIXED"
            else:
                verdict = "INHERIT"  # 未覆写，继承父类行为

            results.append((ent, obf, verdict,
                            ",".join(goal_hits) or "-",
                            ",".join(brain_hits) or "-",
                            super_full or "?"))

    # ── 输出 ──
    print()
    print("=" * 92)
    print("R3 SPIKE — 1.21.1 生物 AI 系统判定（基于官方 mappings + 字节码方法表）")
    print("=" * 92)
    print("%-20s %-8s %-9s %-26s %-22s %s" %
          ("生物", "混淆名", "判定", "Goal方法", "Brain方法", "父类"))
    print("-" * 92)

    groups = {"GOAL": [], "BRAIN": [], "MIXED": [], "INHERIT": [], "other": []}
    for r in results:
        if len(r) == 6:
            ent, obf, verdict, g, b, sup = r
        else:
            ent, obf, verdict, g, b = r
            sup = "?"
        print("%-20s %-8s %-9s %-26s %-22s %s" % (ent, obf, verdict, g, b, sup))
        groups.get(verdict, groups["other"]).append(ent)

    print()
    print("=" * 92)
    print("分组汇总")
    print("=" * 92)
    for k in ["GOAL", "BRAIN", "MIXED", "INHERIT", "other"]:
        if groups[k]:
            print("\n  【%s】共 %d 个" % (k, len(groups[k])))
            for i in range(0, len(groups[k]), 6):
                print("    " + "  ".join("%-18s" % x for x in groups[k][i:i + 6]))

    # 保存 JSON 供后续阶段引用
    out = os.path.join(BASE, "ai_system_map.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "mc_version": "1.21.1",
            "groups": {k: v for k, v in groups.items() if v},
            "detail": [
                {"entity": r[0], "obf": r[1], "verdict": r[2],
                 "goal_methods": r[3], "brain_methods": r[4],
                 "super": r[5] if len(r) == 6 else "?"}
                for r in results
            ],
        }, f, ensure_ascii=False, indent=2)
    print("\n[*] 已保存:", out)


if __name__ == "__main__":
    main()
