"""
关键核实 —— 三个影响 design 核心方案的问题
==============================================

问题 1：GoalSelector 只有 addGoal / getAvailableGoals，没有 removeGoal？
        若为真，「移除索敌 Goal」的实现路径要改变。

问题 2：hurt 方法在哪个类、叫什么名字？
        1.21.1 是 hurt(DamageSource, float) 还是已改名？
        这是仇恨触发的注入点，必须精确。

问题 3：openTradingScreen 在哪里？Merchant 接口里没看到。
        方案 A 若要复用原版 GUI，得知道正确的调用入口。
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


def main():
    n2o, o2n, members = load_mappings()
    zf = open_mc_jar(JAR)
    names = set(zf.namelist())

    def dump_all(fq, title, filt=None):
        print(f"\n{'=' * 74}\n{title}\n  {fq}\n{'=' * 74}")
        obf = n2o.get(fq)
        if not obf:
            print("  ❌ mappings 找不到")
            return None
        entry = f"{obf.replace('.', '/')}.class"
        if entry not in names:
            print(f"  ❌ jar 找不到")
            return None
        info = parse_class(zf.read(entry))
        mem = members.get(fq, {"fields": {}, "methods": {}})
        print("  -- 全部方法 --")
        out = []
        for mname, mdesc, mabs, macc in info["methods"]:
            cands = mem["methods"].get(mname, [])
            rn = cands[0][0] if cands else mname
            rt = cands[0][1] if cands else "?"
            rp = cands[0][2] if cands else "?"
            out.append((rn, rt, rp, macc, mabs))
            if filt and not any(w.lower() in rn.lower() for w in filt):
                continue
            flag = " [abstract]" if mabs else ""
            print(f"    {acc_str(macc):20} {rt:38} {rn}({rp}){flag}")
        return out

    # ── 问题 1：GoalSelector 完整方法列表 ──
    dump_all("net.minecraft.world.entity.ai.goal.GoalSelector",
             "问题 1 —— GoalSelector 的完整 API（是否有 removeGoal？）")

    # WrappedGoal 也看看
    dump_all("net.minecraft.world.entity.ai.goal.WrappedGoal",
             "问题 1b —— WrappedGoal（getAvailableGoals 返回的元素类型）")

    # ── 问题 2：hurt 方法 ──
    for cls, label in [
        ("net.minecraft.world.entity.Entity", "问题 2a —— Entity 的 hurt 系方法"),
        ("net.minecraft.world.entity.LivingEntity", "问题 2b —— LivingEntity 的 hurt 系方法"),
        ("net.minecraft.world.entity.Mob", "问题 2c —— Mob 的 hurt 系方法"),
    ]:
        dump_all(cls, label, filt=["hurt", "damage", "actuallyHurt", "invulnerable"])

    # ── 问题 3：openTradingScreen ──
    for cls, label in [
        ("net.minecraft.world.entity.player.Player", "问题 3a —— Player.openTradingScreen"),
        ("net.minecraft.world.entity.npc.AbstractVillager", "问题 3b —— AbstractVillager 的交易入口"),
    ]:
        dump_all(cls, label, filt=["trad", "Trad", "menu", "Menu", "openMerchant"])

    # ── 补充：HurtByTargetGoal / NearestAttackableTargetGoal ──
    for cls, label in [
        ("net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal",
         "补充 a —— HurtByTargetGoal（受击回击，要保留的）"),
        ("net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal",
         "补充 b —— NearestAttackableTargetGoal（主动索敌，要移除的）"),
        ("net.minecraft.world.entity.ai.goal.target.TargetGoal",
         "补充 c —— TargetGoal 基类"),
    ]:
        dump_all(cls, label)

    print("\n" + "=" * 74)
    print("完成")
    print("=" * 74)


main()
