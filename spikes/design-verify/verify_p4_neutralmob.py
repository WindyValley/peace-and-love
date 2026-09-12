"""
P4 验证 —— 猪灵/疣猪兽已实现的 NeutralMob 是否与本模组冲突
================================================================

背景（ADR-004）：
    猪灵、猪灵蛮兵、疣猪兽、僵尸疣猪兽这 4 个 Brain 系生物
    在原版中**已经实现** NeutralMob 接口。

    本模组也打算复用 NeutralMob 存储仇恨状态。
    需确认：会不会打架？

要查清的问题：
  Q1. 这 4 个生物到底哪些实现了 NeutralMob？（先验证前提是否成立）
  Q2. 它们各自覆写了 NeutralMob 的哪些方法？
  Q3. 有没有调用 forgetCurrentTargetAndRefreshUniversalAnger()？
      —— 这是「对所有玩家记仇」语义，会违反本模组「不扩散到其他玩家」
  Q4. 猪灵的「穿金装中立」逻辑在哪个方法？会不会被我们的改动破坏？
  Q5. 这些生物的 persistentAngerTarget 字段是自己声明的还是继承的？
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

TARGETS = {
    "net.minecraft.world.entity.monster.piglin.Piglin": "猪灵",
    "net.minecraft.world.entity.monster.piglin.PiglinBrute": "猪灵蛮兵",
    "net.minecraft.world.entity.monster.hoglin.Hoglin": "疣猪兽",
    "net.minecraft.world.entity.monster.Zoglin": "僵尸疣猪兽",
    "net.minecraft.world.entity.monster.warden.Warden": "监守者",
    "net.minecraft.world.entity.monster.breeze.Breeze": "旋风人",
}

NEUTRAL_MOB = "net.minecraft.world.entity.NeutralMob"

# NeutralMob 的方法（官方名）
NM_METHODS = {
    "getRemainingPersistentAngerTime", "setRemainingPersistentAngerTime",
    "getPersistentAngerTarget", "setPersistentAngerTarget",
    "startPersistentAngerTimer", "isAngry", "stopBeingAngry",
    "forgetCurrentTargetAndRefreshUniversalAnger",
    "addPersistentAngerSaveData", "readPersistentAngerSaveData",
    "updatePersistentAnger", "playerDied",
}

DANGER = "forgetCurrentTargetAndRefreshUniversalAnger"


def get_refs(data, cp):
    """提取 class 常量池中引用的所有方法名（utf8 条目）"""
    out = set()
    for k, v in cp.items():
        if v[0] == "utf8":
            out.add(v[1])
    return out


def parse_with_cp(data):
    """parse_class 的变体，额外返回常量池里的全部 utf8 字符串"""
    if data[:4] != b"\xca\xfe\xba\xbe":
        return None, set()
    off = 8
    cp_count = struct.unpack(">H", data[off:off + 2])[0]
    off += 2
    strings = set()
    i = 1
    while i < cp_count:
        tag = data[off]
        off += 1
        if tag == 1:
            ln = struct.unpack(">H", data[off:off + 2])[0]
            off += 2
            strings.add(data[off:off + ln].decode("utf-8", "replace"))
            off += ln
        else:
            _, size = CP_TAGS.get(tag, (None, None))
            if size is None:
                return None, strings
            off += size
            if tag in (5, 6):
                i += 1
        i += 1
    return parse_class(data), strings


def main():
    n2o, o2n, members = load_mappings()
    zf = open_mc_jar(JAR)
    names = set(zf.namelist())

    nm_obf = n2o.get(NEUTRAL_MOB)
    print("=" * 78)
    print("P4 —— 猪灵/疣猪兽的 NeutralMob 冲突检查")
    print("=" * 78)
    print(f"\nNeutralMob 混淆名：{nm_obf}")

    # NeutralMob 各方法的混淆名
    nm_mem = members.get(NEUTRAL_MOB, {"methods": {}})
    nm_obf_by_real = {}
    for obf, cands in nm_mem["methods"].items():
        for real, ret, params in cands:
            nm_obf_by_real.setdefault(real, set()).add(obf)
    print("NeutralMob 方法混淆映射：")
    for real in sorted(NM_METHODS):
        if real in nm_obf_by_real:
            print(f"    {real:48} -> {sorted(nm_obf_by_real[real])}")

    print("\n" + "=" * 78)
    print("逐个生物检查")
    print("=" * 78)

    for fq, zh in TARGETS.items():
        obf = n2o.get(fq)
        print(f"\n{'─' * 78}")
        print(f"■ {zh}  ({fq.split('.')[-1]})")
        print(f"{'─' * 78}")
        if not obf:
            print("  ❌ mappings 找不到")
            continue
        entry = f"{obf.replace('.', '/')}.class"
        if entry not in names:
            print(f"  ❌ jar 找不到 {entry}")
            continue

        info, strings = parse_with_cp(zf.read(entry))
        if not info:
            print("  ❌ 解析失败")
            continue

        # Q1: 是否实现 NeutralMob
        ifaces = [x.replace("/", ".") for x in info["ifaces"]]
        iface_real = [o2n.get(x, x) for x in ifaces]
        has_nm = nm_obf in ifaces
        print(f"  实现 NeutralMob：{'✅ 是' if has_nm else '❌ 否'}")
        print(f"  接口列表：{[x.split('.')[-1] for x in iface_real]}")

        sup = info["super"].replace("/", ".") if info["super"] else None
        print(f"  父类：{o2n.get(sup, sup).split('.')[-1] if sup else '—'}")

        if not has_nm:
            continue

        # Q2: 覆写了哪些 NeutralMob 方法
        mem = members.get(fq, {"methods": {}, "fields": {}})
        overridden = []
        for mname, mdesc, mabs, macc in info["methods"]:
            cands = mem["methods"].get(mname, [])
            for real, ret, params in cands:
                if real in NM_METHODS:
                    overridden.append((real, params))
        if overridden:
            print(f"  覆写的 NeutralMob 方法（{len(set(x[0] for x in overridden))} 个）：")
            for real, params in sorted(set(overridden)):
                print(f"      {real}({params})")

        # Q3: 是否引用危险方法
        danger_obf = nm_obf_by_real.get(DANGER, set())
        hits = [s for s in strings if s in danger_obf]
        # 也直接找官方名（有些是 SRG/未混淆）
        if DANGER in strings:
            hits.append(DANGER)
        print(f"  引用 {DANGER}：{'⚠️ 是 → ' + str(hits) if hits else '✅ 否'}")

        # Q5: 自己声明的 anger 相关字段
        anger_fields = []
        for fname, fdesc, facc in info["fields"]:
            real = mem["fields"].get(fname)
            rn = real[1] if real else fname
            if any(k in rn.lower() for k in ["anger", "angry", "target", "persistent"]):
                anger_fields.append((rn, real[0] if real else fdesc, acc_str(facc)))
        if anger_fields:
            print(f"  自有 anger 相关字段（{len(anger_fields)}）：")
            for rn, rt, ac in anger_fields:
                print(f"      {ac:18} {rt:44} {rn}")
        else:
            print("  自有 anger 相关字段：无（全部继承）")

    # Q4: 猪灵「穿金装中立」逻辑
    print("\n" + "=" * 78)
    print("Q4 —— 猪灵「穿金装中立」逻辑定位")
    print("=" * 78)
    for cand in ["net.minecraft.world.entity.monster.piglin.PiglinAi",
                 "net.minecraft.world.entity.monster.piglin.Piglin"]:
        obf = n2o.get(cand)
        if not obf:
            continue
        entry = f"{obf.replace('.', '/')}.class"
        if entry not in names:
            continue
        mem = members.get(cand, {"methods": {}})
        interesting = []
        for obf_m, cands in mem["methods"].items():
            for real, ret, params in cands:
                if any(k in real.lower() for k in
                       ["gold", "wearing", "armor", "isadult", "angerpreventedby",
                        "wasHurtBy", "setangertarget", "getangertarget", "stopholding"]):
                    interesting.append((real, ret, params))
        if interesting:
            print(f"\n  {cand.split('.')[-1]}:")
            for real, ret, params in sorted(set(interesting)):
                print(f"      {ret.split('.')[-1]:22} {real}({params})")

    print("\n" + "=" * 78)
    print("完成")
    print("=" * 78)


main()
