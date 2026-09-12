"""
P4 v3 —— 精确检查真正有交集的 2 个生物
==========================================
v2 的 cls_to_id 把 EnderMan 转成 "ender_man"，与适配列表里的 "enderman" 不匹配，
漏掉了末影人。实际交集是 2 个：

  1. minecraft:enderman          (Goal 系)  —— EnderMan implements NeutralMob
  2. minecraft:zombified_piglin  (Goal 系)  —— ZombifiedPiglin implements NeutralMob

本脚本逐个检查这两个生物与本模组 AngerController 的冲突点。
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
DANGER = "forgetCurrentTargetAndRefreshUniversalAnger"

CONFLICT = {
    "net.minecraft.world.entity.monster.EnderMan": "末影人",
    "net.minecraft.world.entity.monster.ZombifiedPiglin": "僵尸猪灵",
}

NM_METHODS = {
    "getRemainingPersistentAngerTime", "setRemainingPersistentAngerTime",
    "getPersistentAngerTarget", "setPersistentAngerTarget",
    "startPersistentAngerTimer", "isAngry", "stopBeingAngry",
    "forgetCurrentTargetAndRefreshUniversalAnger",
    "addPersistentAngerSaveData", "readPersistentAngerSaveData",
    "updatePersistentAnger", "playerDied",
}


def parse_with_strings(data):
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

    nm_mem = members.get(NEUTRAL_MOB, {"methods": {}})
    danger_obf = set()
    for obf, cands in nm_mem["methods"].items():
        for real, ret, params in cands:
            if real == DANGER:
                danger_obf.add(obf)

    print("=" * 78)
    print("P4 v3 —— 与本模组有交集的 2 个生物的冲突分析")
    print("=" * 78)
    print(f"\n危险方法 {DANGER} 的混淆名：{sorted(danger_obf)}")
    print("（该方法有 universal anger 语义 = 对所有玩家记仇，")
    print("  会违反本模组「仇恨不扩散到其他玩家」的需求）")

    for fq, zh in CONFLICT.items():
        obf = n2o.get(fq)
        print(f"\n{'=' * 78}")
        print(f"■ {zh}  ({fq.split('.')[-1]})  混淆名 {obf}")
        print(f"{'=' * 78}")
        entry = f"{obf.replace('.', '/')}.class"
        info, strings = parse_with_strings(zf.read(entry))
        mem = members.get(fq, {"methods": {}, "fields": {}})

        # 覆写的 NeutralMob 方法
        ov = set()
        for mname, mdesc, mabs, macc in info["methods"]:
            for real, ret, params in mem["methods"].get(mname, []):
                if real in NM_METHODS:
                    ov.add((real, params))
        print(f"\n  覆写的 NeutralMob 方法（{len(ov)}）：")
        for real, params in sorted(ov):
            print(f"      {real}({params})")

        # anger 字段
        print("\n  自有 anger 相关字段：")
        got = False
        for fname, fdesc, facc in info["fields"]:
            real = mem["fields"].get(fname)
            rn = real[1] if real else fname
            rt = real[0] if real else fdesc
            if any(k in rn.lower() for k in
                   ["anger", "angry", "persistent", "target", "provoc"]):
                print(f"      {acc_str(facc):22} {rt:40} {rn}")
                got = True
        if not got:
            print("      （无）")

        # 是否引用危险方法
        hits = [s for s in strings if s in danger_obf]
        print(f"\n  引用 {DANGER}：")
        if hits:
            print(f"      ⚠️  是 → 常量池中出现 {hits}")
            print("      需确认调用上下文（可能是自己实现该方法，而非调用）")
            # 判断是「实现」还是「调用」
            impl = any(real == DANGER for real, _ in ov)
            print(f"      本类是否覆写该方法：{'✅ 是（属实现，非调用）' if impl else '❌ 否（可能是调用）'}")
        else:
            print("      ✅ 否")

        # 该生物的特殊中立逻辑
        print("\n  特殊行为方法（本模组需注意）：")
        special = []
        for obf_m, cands in mem["methods"].items():
            for real, ret, params in cands:
                if any(k in real.lower() for k in
                       ["isangry", "islookingat", "provok", "beingstared",
                        "hurt", "settarget", "canattack", "playerdied",
                        "readditional", "addadditional", "customserver"]):
                    special.append((real, ret.split(".")[-1], params))
        for real, ret, params in sorted(set(special)):
            print(f"      {ret:26} {real}({params})")

    print("\n" + "=" * 78)
    print("结论")
    print("=" * 78)
    print("""
  本模组 38 个已适配生物中，仅 2 个原版实现了 NeutralMob：
      · minecraft:enderman         （Goal 系）
      · minecraft:zombified_piglin （Goal 系）

  ⚠️ 注意：这 2 个都是 **Goal 系**，不是先前 ADR-004 中所说的
     「猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽 4 个 Brain 系生物」。
     ADR-004 的 P4 描述有误，需要修正。
""")


main()
