"""
核查：末影龙与凋灵被 classify_v3 判为「Goal 系统」是否可信？
==============================================================

怀疑理由：
  classify_v3 的判据是「是否覆写 makeBrain/brainProvider」。
  不覆写 → 判为 Goal。

  但末影龙用的是 DragonPhaseInstance（Phase 系统），
  它既不是 Brain，也不是标准的 goalSelector/targetSelector。
  「不是 Brain」≠「是 Goal」—— 这是个二分法漏洞。

本脚本直接检查这两个类是否真的持有 goalSelector / targetSelector，
以及它们的类继承链，给出准确结论。
"""

import io
import re
import struct
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
JAR = BASE / "server-1.21.1.jar"
MAPPINGS = BASE / "server_mappings.txt"


def open_inner_jar(path):
    z = zipfile.ZipFile(path)
    inner = [n for n in z.namelist() if n.endswith(".jar") and "server" in n]
    if inner:
        with z.open(inner[0]) as f:
            return zipfile.ZipFile(io.BytesIO(f.read()))
    return z


def parse_mappings(path):
    out, cur = {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            if not raw.startswith("    "):
                m = re.match(r"^(\S+) -> (\S+):$", raw.strip())
                if m:
                    cur = m.group(1)
                    out[cur] = {"obf": m.group(2), "methods": {}, "fields": {}}
            else:
                if cur is None:
                    continue
                s = raw.strip()
                mm = re.match(r"^(?:\d+:\d+:)?(\S+) (\S+)\((.*?)\) -> (\S+)$", s)
                if mm:
                    out[cur]["methods"].setdefault(mm.group(2), mm.group(4))
                    continue
                fm = re.match(r"^(\S+) (\S+) -> (\S+)$", s)
                if fm:
                    out[cur]["fields"].setdefault(fm.group(2), fm.group(3))
    return out


def parse_class(data):
    if not data or data[:4] != b"\xca\xfe\xba\xbe":
        return None
    pos = 8
    cpc = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    cp = {}
    i = 1
    while i < cpc:
        tag = data[pos]; pos += 1
        if tag == 1:
            ln = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            cp[i] = data[pos:pos + ln].decode("utf-8", "replace"); pos += ln
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = ("ref", struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        elif tag == 15:
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            cp[i] = ("ref2", struct.unpack(">HH", data[pos:pos + 4])); pos += 4
        elif tag in (5, 6):
            pos += 8; i += 1
        else:
            return None
        i += 1

    def cls_name(idx):
        v = cp.get(idx)
        if isinstance(v, tuple) and v[0] == "ref":
            return cp.get(v[1])
        return None

    pos += 2
    this_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    super_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    ic = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    ifaces = []
    for _ in range(ic):
        ifaces.append(cls_name(struct.unpack(">H", data[pos:pos + 2])[0])); pos += 2

    res = {}
    for label in ("fields", "methods"):
        n = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        lst = []
        for _ in range(n):
            acc = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            nm = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
            dc = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
            lst.append((nm, dc, acc))
            ac = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            for _ in range(ac):
                pos += 2
                al = struct.unpack(">I", data[pos:pos + 4])[0]; pos += 4 + al
        res[label] = lst

    return {"this": cls_name(this_i), "super": cls_name(super_i),
            "interfaces": ifaces, **res,
            "all_strings": [v for v in cp.values() if isinstance(v, str)]}


CHECK = {
    "末影龙":  "net.minecraft.world.entity.boss.enderdragon.EnderDragon",
    "凋灵":    "net.minecraft.world.entity.boss.wither.WitherBoss",
    "潜影贝":  "net.minecraft.world.entity.monster.Shulker",
    "幻翼":    "net.minecraft.world.entity.monster.Phantom",
    "恼鬼":    "net.minecraft.world.entity.monster.Vex",
    "僵尸(对照)": "net.minecraft.world.entity.monster.Zombie",
}


def main():
    print("=" * 86)
    print("核查：Boss 与特殊生物是否真的持有 goalSelector / targetSelector")
    print("=" * 86)

    maps = parse_mappings(MAPPINGS)
    jar = open_inner_jar(JAR)

    # Mob 基类中 goalSelector / targetSelector 的混淆名
    mob_fq = "net.minecraft.world.entity.Mob"
    goal_obf = maps[mob_fq]["fields"].get("goalSelector")
    target_obf = maps[mob_fq]["fields"].get("targetSelector")
    print(f"\n  Mob.goalSelector   -> {goal_obf}")
    print(f"  Mob.targetSelector -> {target_obf}")
    print(f"  Mob 混淆名          -> {maps[mob_fq]['obf']}")

    # PathfinderMob / Monster 继承链
    print("\n【1】继承链与 Mob 基类的关系\n")
    for zh, fq in CHECK.items():
        if fq not in maps:
            print(f"  {zh:12} ⚠️ mappings 未找到")
            continue
        obf = maps[fq]["obf"]
        chain = []
        cur_obf = obf
        for _ in range(8):
            try:
                d = jar.read(cur_obf.replace(".", "/") + ".class")
            except KeyError:
                break
            info = parse_class(d)
            if not info:
                break
            # 反查 named
            named = None
            for k, v in maps.items():
                if v["obf"] == cur_obf:
                    named = k.split(".")[-1]
                    break
            chain.append(named or cur_obf)
            sup = info["super"]
            if not sup or sup == "java/lang/Object":
                break
            sup_dotted = sup.replace("/", ".")
            cur_obf = sup_dotted
        print(f"  {zh:12} {' → '.join(chain[:6])}")

    # 检查是否在自己类中引用 goalSelector / targetSelector
    print("\n【2】是否在自身字节码中引用 goalSelector / targetSelector\n")
    print("  （引用 = 该类自己往里面 addGoal，说明确实用 Goal 系统）\n")
    for zh, fq in CHECK.items():
        if fq not in maps:
            continue
        obf = maps[fq]["obf"]
        try:
            d = jar.read(obf.replace(".", "/") + ".class")
        except KeyError:
            print(f"  {zh:12} ⚠️ jar 未找到")
            continue
        info = parse_class(d)
        if not info:
            continue
        strs = set(info["all_strings"])
        has_goal = goal_obf in strs
        has_target = target_obf in strs
        # 检查是否有 registerGoals 方法
        reg_obf = maps.get(fq, {}).get("methods", {}).get("registerGoals")
        declared = {m[0] for m in info["methods"]}
        has_reg = reg_obf in declared if reg_obf else False

        marks = []
        if has_goal:
            marks.append("引用goalSelector")
        if has_target:
            marks.append("引用targetSelector")
        if has_reg:
            marks.append("覆写registerGoals")
        print(f"  {zh:12} {', '.join(marks) if marks else '❌ 均未引用'}")

    # 末影龙特有：DragonPhaseInstance
    print("\n【3】末影龙的 Phase 系统佐证\n")
    ed_fq = CHECK["末影龙"]
    ed_obf = maps[ed_fq]["obf"]
    d = jar.read(ed_obf.replace(".", "/") + ".class")
    info = parse_class(d)
    phase_fq = "net.minecraft.world.entity.boss.enderdragon.phases.EnderDragonPhaseManager"
    if phase_fq in maps:
        pm_obf = maps[phase_fq]["obf"]
        found = pm_obf in set(info["all_strings"]) or \
            any(pm_obf in s for s in info["all_strings"] if isinstance(s, str))
        print(f"  EnderDragonPhaseManager 混淆名: {pm_obf}")
        print(f"  末影龙类中引用该类: {'✅ 是' if found else '❌ 否'}")
    print(f"  末影龙字段数: {len(info['fields'])}, 方法数: {len(info['methods'])}")

    print("\n" + "=" * 86)
    print("【4】结论")
    print("=" * 86)
    print("""
  ⚠️ classify_v3 的二分法有漏洞：「不覆写 makeBrain」→ 判为 Goal，
     但实际上存在第三类：**既非 Goal 也非 Brain 的自有 AI**。

  准确的三分法应为：
     ① Goal 系统    —— 继承 Mob，用 goalSelector/targetSelector，覆写 registerGoals
     ② Brain 系统   —— 覆写 makeBrain/brainProvider
     ③ 自有 AI      —— 末影龙的 Phase 系统；不走前两者

  请以上面【1】【2】的实测输出为准判断各生物归属。
""")


if __name__ == "__main__":
    main()
