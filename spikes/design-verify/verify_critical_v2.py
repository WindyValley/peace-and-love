"""
关键核实 v2 —— 修正 mappings 反查歧义
========================================

v1 缺陷：多个不同方法可能被混淆成同一个短名（如都叫 'a'），
        `members[cls]['methods'][obf_name]` 是一个候选列表，
        v1 无脑取 [0]，导致 hurt/removeGoal 等被同名方法顶掉。

v2 修正：用 JVM 描述符的参数类型与 mappings 记录的参数列表做匹配，
        精确定位到唯一的官方方法名。
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

PRIM = {"B": "byte", "C": "char", "D": "double", "F": "float",
        "I": "int", "J": "long", "S": "short", "Z": "boolean", "V": "void"}


def parse_desc(desc):
    """JVM 描述符 -> (参数类型列表, 返回类型)，均为官方风格的 java 类型名"""
    def one(s, i):
        arr = 0
        while s[i] == "[":
            arr += 1
            i += 1
        if s[i] == "L":
            j = s.index(";", i)
            t = s[i + 1:j].replace("/", ".")
            i = j + 1
        else:
            t = PRIM[s[i]]
            i += 1
        return t + "[]" * arr, i

    assert desc[0] == "("
    i = 1
    params = []
    while desc[i] != ")":
        t, i = one(desc, i)
        params.append(t)
    ret, _ = one(desc, i + 1)
    return params, ret


def build_resolver(o2n, members):
    """返回 resolve(cls_fq, obf_method_name, jvm_desc) -> 官方方法名"""
    def resolve(fq, obf_name, desc):
        mem = members.get(fq)
        if not mem:
            return None
        cands = mem["methods"].get(obf_name)
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0][0]
        params, ret = parse_desc(desc)
        want = ",".join(params)
        for real_name, real_ret, real_params in cands:
            if real_params == want:
                return real_name
        # 参数匹配不上时退回参数个数匹配
        for real_name, real_ret, real_params in cands:
            n = len([x for x in real_params.split(",") if x])
            if n == len(params):
                return real_name
        return cands[0][0]
    return resolve


def main():
    n2o, o2n, members = load_mappings()
    resolve = build_resolver(o2n, members)
    zf = open_mc_jar(JAR)
    names = set(zf.namelist())

    def dump(fq, title, filt=None, show_fields=False):
        print(f"\n{'=' * 76}\n{title}\n  {fq}\n{'=' * 76}")
        obf = n2o.get(fq)
        if not obf:
            print("  ❌ mappings 找不到")
            return
        entry = f"{obf.replace('.', '/')}.class"
        if entry not in names:
            print("  ❌ jar 找不到")
            return
        info = parse_class(zf.read(entry))
        mem = members.get(fq, {"fields": {}, "methods": {}})

        if show_fields:
            print("  -- 字段 --")
            for fname, fdesc, facc in info["fields"]:
                real = mem["fields"].get(fname)
                rn = real[1] if real else fname
                rt = real[0] if real else fdesc
                print(f"    {acc_str(facc):22} {rt:44} {rn}")
            print()

        print("  -- 方法 --")
        rows = []
        for mname, mdesc, mabs, macc in info["methods"]:
            rn = resolve(fq, mname, mdesc) or mname
            params, ret = parse_desc(mdesc)
            short_p = ", ".join(p.split(".")[-1] for p in params)
            short_r = ret.split(".")[-1]
            rows.append((rn, short_r, short_p, macc, mabs))

        hit = False
        for rn, ret, params, macc, mabs in sorted(rows):
            if filt and not any(w.lower() in rn.lower() for w in filt):
                continue
            hit = True
            flag = " [abstract]" if mabs else ""
            print(f"    {acc_str(macc):20} {ret:26} {rn}({params}){flag}")
        if not hit:
            print("    (无匹配项)")

    print("=" * 76)
    print("关键核实 v2 —— 描述符精确匹配")
    print("=" * 76)

    dump("net.minecraft.world.entity.ai.goal.GoalSelector",
         "★ 问题 1 —— GoalSelector 完整 API（有没有 removeGoal？）")

    dump("net.minecraft.world.entity.Entity",
         "★ 问题 2a —— Entity.hurt", filt=["hurt", "invulnerable"])

    dump("net.minecraft.world.entity.LivingEntity",
         "★ 问题 2b —— LivingEntity.hurt / 记仇相关",
         filt=["hurt", "LastHurt", "setLastHurt"])

    dump("net.minecraft.world.entity.Mob",
         "★ 问题 2c —— Mob.hurt / target / mobInteract",
         filt=["hurt", "Target", "mobInteract", "registerGoals", "SaveData"])

    dump("net.minecraft.world.entity.player.Player",
         "★ 问题 3a —— Player.openTradingScreen",
         filt=["trad", "merchant", "openMenu"])

    dump("net.minecraft.world.entity.npc.AbstractVillager",
         "★ 问题 3b —— AbstractVillager 交易入口",
         filt=["trad", "Offer", "menu", "mobInteract", "Merchant"])

    dump("net.minecraft.world.entity.npc.Villager",
         "★ 问题 3c —— Villager 补货机制",
         filt=["estock", "Restock", "Gossip"])

    dump("net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal",
         "补充 a —— HurtByTargetGoal（保留）")

    dump("net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal",
         "补充 b —— NearestAttackableTargetGoal（移除对象）")

    print("\n" + "=" * 76)
    print("完成")
    print("=" * 76)


main()
