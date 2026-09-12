"""
R2 spike 追加验证 —— 「每日补货」能否直接用原版机制表达
==========================================================

用户提问（2026-09-11）：
    「每天一次能否通过补货频率控制？这里实际想要达成的效果是
      每天最多购买到单次击杀时能获取的掉落物上限」

要验证的假设：
    maxUses = 1  +  每游戏日补货一次  ≡  「每天最多买到一次击杀的量」

复用 analyze.py 中已验证可用的 jar 解包与 class 解析实现，
不重复造轮子（先前自写版本因常量池解析 bug 返回 None）。
"""

import importlib.util
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
JAR = BASE.parent / "r3-ai" / "server-1.21.1.jar"
MAPPINGS = BASE.parent / "r3-ai" / "server_mappings.txt"

# ── 复用 analyze.py 的实现 ──
_spec = importlib.util.spec_from_file_location("r2_analyze", BASE / "analyze.py")
_an = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_an)

open_inner_jar = _an.open_inner_jar
read_class = _an.read_class
parse_class = _an.parse_class


def load_mappings():
    """named class -> [(kind, named, obf, rtype, params)]"""
    n2o, members = {}, {}
    cur = None
    with open(MAPPINGS, encoding="utf-8") as f:
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
                    n2o[cur] = m.group(2)
                    members[cur] = []
            else:
                if cur is None:
                    continue
                s = raw.strip()
                mm = re.match(r"^(?:\d+:\d+:)?(\S+) (\S+)\((.*?)\) -> (\S+)$", s)
                if mm:
                    members[cur].append(
                        ("method", mm.group(2), mm.group(4), mm.group(1), mm.group(3)))
                    continue
                fm = re.match(r"^(\S+) (\S+) -> (\S+)$", s)
                if fm:
                    members[cur].append(
                        ("field", fm.group(2), fm.group(3), fm.group(1), ""))
    return n2o, members


ACC = [(0x0001, "public"), (0x0002, "private"), (0x0004, "protected"),
       (0x0008, "static"), (0x0010, "final"), (0x0400, "abstract")]


def flags(a):
    return " ".join(v for k, v in ACC if a & k) or "package"


TARGETS = {
    "Villager":         "net.minecraft.world.entity.npc.Villager",
    "MerchantOffer":    "net.minecraft.world.item.trading.MerchantOffer",
    "Merchant":         "net.minecraft.world.item.trading.Merchant",
}


def main():
    print("=" * 84)
    print("R2 追加验证 —— 「每日补货」能否用原版机制直接表达")
    print("=" * 84)

    n2o, members = load_mappings()
    jar = open_inner_jar(JAR)

    # ─── 1. 补货相关方法 ───
    print("\n【1】Villager 补货相关方法（官方 mappings）\n")
    vfq = TARGETS["Villager"]
    want_v = {"restock", "shouldRestock", "needsToRestock", "catchUpDemand",
              "updateDemand", "resetNumberOfRestocks", "tickDownDemand"}
    for kind, named, obf, rt, pr in members[vfq]:
        if kind == "method" and named in want_v:
            print(f"  {rt.split('.')[-1]:10} {named:24} -> {obf}")

    print("\n【2】Villager 补货相关字段\n")
    for kind, named, obf, rt, pr in members[vfq]:
        if kind == "field" and any(
                k in named.lower() for k in ("restock", "numberof")):
            print(f"  {rt.split('.')[-1]:10} {named:28} -> {obf}")

    # ─── 3. MerchantOffer 字段 ───
    print("\n【3】MerchantOffer 的字段（决定交易次数语义）\n")
    mo_fq = TARGETS["MerchantOffer"]
    data = read_class(jar, n2o[mo_fq])
    info = parse_class(data)
    if info is None:
        print("  ⚠️  解析失败")
    else:
        fidx = {ob: (nm, rt) for kind, nm, ob, rt, pr in members[mo_fq]
                if kind == "field"}
        # analyze.py 的 parse_class 返回 fields 为 (name, desc, access)
        for fname, fdesc, facc in info["fields"]:
            hit = fidx.get(fname)
            if not hit:
                continue
            named, rtype = hit
            mark = ""
            if named in ("uses", "maxUses"):
                mark = "   ★ 交易次数核心"
            print(f"  {flags(facc):22} {rtype.split('.')[-1]:14} {named}{mark}")

    # ─── 4. MerchantOffer 补货相关方法 ───
    print("\n【4】MerchantOffer 交易次数相关方法\n")
    want_mo = {"resetUses", "increaseUses", "isOutOfStock", "getUses",
               "getMaxUses", "setToOutOfStock"}
    for kind, named, obf, rt, pr in members[mo_fq]:
        if kind == "method" and named in want_mo:
            print(f"  {rt.split('.')[-1]:10} {named:20} -> {obf}")

    # ─── 5. Merchant 接口 abstract vs default ───
    print("\n【5】Merchant 接口：abstract vs default\n")
    mc_fq = TARGETS["Merchant"]
    data = read_class(jar, n2o[mc_fq])
    info = parse_class(data)
    if info is None:
        print("  ⚠️  解析失败")
    else:
        midx = {ob: nm for kind, nm, ob, rt, pr in members[mc_fq]
                if kind == "method"}
        abs_l, def_l = [], []
        for mname, mdesc, mabs, macc in info["methods"]:
            if mname in ("<init>", "<clinit>"):
                continue
            nm = midx.get(mname, mname)
            (abs_l if mabs else def_l).append(nm)
        print(f"  必须自己实现（abstract）：{len(abs_l)} 个")
        for n in abs_l:
            print(f"     · {n}")
        print(f"\n  原版已给实现（default）：{len(def_l)} 个  ← 白送")
        for n in def_l:
            print(f"     ✅ {n}")

    # ─── 结论 ───
    print("\n" + "=" * 84)
    print("【6】结论")
    print("=" * 84)
    print("""
  ✅ 用户的思路成立，而且比我先前的设计更简单。

     原版已具备的机制：
       MerchantOffer.uses / maxUses     交易次数计数
       MerchantOffer.resetUses()        把 uses 清零 = 补货
       MerchantOffer.isOutOfStock()     判断是否已售罄
       Villager.restock()               批量补货
       Villager.shouldRestock()         判断补货时机
       Villager.lastRestockGameTime     上次补货的游戏时间
       Villager.numberOfRestocksToday   当天已补货次数

     所以：
       maxUses = 1  +  每游戏日 restock() 一次
       ≡ 「每天最多买到一次击杀能拿到的量」

  ❌ 先前设想的 Map<ItemId, lastTradeDay> 是多余的，撤销该设计。
     实体 NBT 只需存一个 long: lastRestockDay。

  实现要点：
     ① 生成 offer 时 maxUses = 1（配置项 max_uses_per_day，默认 1）
     ② result 数量 = 该掉落物「一次击杀最大掉落数」（R1 已能算出）
     ③ 自实现 shouldRestock()：currentDay > lastRestockDay 则 restock()
        补货周期作为配置项 restock_interval_days，默认 1
     ④ 不照抄 Villager 的「每天 2 次」上限与 catchUpDemand 价格波动，
        我们只要「清零 uses」这一件事，写个精简版

  ⚠️ 注意：Villager.restock() 内部还耦合了 gossip / demand / 价格波动，
     不能直接调用，需自己写 resetAllUses()。
""")


if __name__ == "__main__":
    main()
