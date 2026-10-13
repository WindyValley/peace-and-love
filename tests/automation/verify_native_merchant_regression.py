#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交易健壮性：原生 Merchant（村民 / 流浪商人）交易零回归真机验证。

目的：MobMerchantMixin 打在 Mob 基类上，确认它不干扰已实现 Merchant 接口的
原生商人——能正常开窗、原生成交、uses 走原版，且 Mixin 的持久化字段
(pal_offers/pal_sig) 不会写进原生商人存档（AbstractVillager 自带 "Offers"）。

用确定性 Offers NBT（1 绿宝石 -> 1 面包，maxUses=5），通用 trade.* RPC 对
村民 MerchantMenu 同样适用。前置：Dev 客户端已连 192.0.2.10。
"""
import subprocess, sys, time, uuid

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

passed, failed = [], []
def check(name, cond, extra=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + ("  " + str(extra) if extra else ""))
    if not cond:
        raise AssertionError(name)

def rcon(c, expect=True):
    r = server_rcon(c)
    if expect and ("No player" in r or "Could not" in r or "Failed" in r or "Unknown" in r):
        raise RuntimeError(f"RCON 失败: {c} -> {r}")
    return r

def wait(pred, sec=8, step=0.25):
    end=time.time()+sec; last=None
    while time.time()<end:
        try:
            v=pred()
            if v: return v
        except Exception as e: last=e
        time.sleep(step)
    if last: raise last
    return None

# 确定性报价：1 绿宝石买 1 面包，maxUses=1（trade.take 是 shift-click 批量成交，
# 用 maxUses=1 保证单次成交确定：1 面包、uses=1；不影响"验证原生交易正常"的目的）
OFFERS = ('{VillagerData:{profession:"minecraft:armorer",level:2,type:"minecraft:plains"},'
          'Offers:{Recipes:[{buy:{id:"minecraft:emerald",count:1},'
          'sell:{id:"minecraft:bread",count:1},maxUses:1,priceMultiplier:0.0f,'
          'demand:0,xp:0,specialPrice:0,xp2:0}]}}')

MERCHANTS = [
    ("villager", "minecraft:villager", OFFERS),
    ("wandering_trader", "minecraft:wandering_trader",
     '{Offers:{Recipes:[{buy:{id:"minecraft:emerald",count:1},sell:{id:"minecraft:bread",count:1},'
     'maxUses:1,priceMultiplier:0.0f,demand:0,xp:0,specialPrice:0,xp2:0}]}}'),
]

def run_merchant(label, etype, nbt):
    print(f"\n===== 原生商人零回归：{label} =====")
    tag = "PALN-" + uuid.uuid4().hex[:6]
    tkey = etype.split(":")[-1]  # nearestByType 用不带命名空间的 id
    # 清掉同类野生实体，避免 nearestByType 选到 32 格内别的同类
    rcon(f"kill @e[type={etype}]", expect=False)
    time.sleep(0.3)
    # 固定隔间（同 verify_trade_purchase 已验证范式）：玩家在格中心，怪东侧相邻格
    IX, IY, IZ = 120, -57, 60
    rcon(f"tp Dev {IX+0.5} {IY} {IZ+0.5}")
    time.sleep(0.3)
    # nbt 形如 "{...}"，在尾括号前插入定点/标签字段
    full_nbt = nbt[:-1] + (f",NoAI:1b,PersistenceRequired:1b,Tags:[\"{tag}\"]" + "}")
    rcon(f"summon {etype} {IX+1} {IY} {IZ} {full_nbt}")
    time.sleep(0.8)
    rcon("item replace entity Dev weapon.mainhand with air"); rcon("item replace entity Dev weapon.offhand with air")
    time.sleep(0.2)
    try:
        # 1) 空手右键原生商人必须开窗（重试，同购买脚本范式）
        r = None
        for _ in range(3):
            try:
                rr = rpc("player.interact", {"target": tkey, "autoClose": False}, timeout=15)
                if rr.get("screenOpen"):
                    r = rr; break
            except RuntimeError as e:
                print("  interact 重试:", e)
            time.sleep(1.0)
        check(f"[{label}] 右键打开原生交易 GUI", bool(r), r)

        # 开窗后给绿宝石
        rcon("give Dev emerald 16"); time.sleep(0.4)
        st = rpc("trade.status")
        offers = st.get("offers", [])
        check(f"[{label}] 读到原生报价(面包)", any(o.get("result")=="minecraft:bread" for o in offers), offers)
        idx = next(i for i,o in enumerate(offers) if o.get("result")=="minecraft:bread")

        before_bread = st.get("inventory", {}).get("minecraft:bread", 0)
        rpc("trade.select", {"index": idx}); time.sleep(0.4)
        st = rpc("trade.status")
        check(f"[{label}] select 后货币槽有绿宝石、结果槽面包",
              st.get("costA",{}).get("item")=="minecraft:emerald"
              and st.get("result",{}).get("item")=="minecraft:bread",
              {'costA':st.get("costA"),'result':st.get("result")})
        rpc("trade.take"); time.sleep(0.5)
        st = rpc("trade.status")
        after_bread = st.get("inventory", {}).get("minecraft:bread", 0)
        uses = offers and st.get("offers",[{}])[idx].get("uses")
        check(f"[{label}] 原生成交：面包入包、uses+1", after_bread >= before_bread+1 and uses==1,
              {'bread':f"{before_bread}->{after_bread}",'uses':uses})

        # 2) 关键：Mixin 持久化字段不得写进原生商人存档
        rcon("save-all"); time.sleep(1.0)
        bad = rcon(f"data get entity @e[type={etype},tag={tag},limit=1] pal_offers", expect=False)
        missing = ("Unable to locate" in bad) or ("Found no" in bad) or ("No NBT element" in bad)
        check(f"[{label}] 存档无 pal_offers 污染", missing, bad.strip()[:90])
        # 原版 Offers 字段应存在
        good = rcon(f"data get entity @e[type={etype},tag={tag},limit=1] Offers", expect=False)
        check(f"[{label}] 保留原版 Offers 字段", "Recipes" in good or "offers" in good.lower(), good.strip()[:80])
    finally:
        try: rpc("trade.close", timeout=5)
        except Exception: pass
        time.sleep(0.3)
        rcon(f"kill @e[type={etype},tag={tag}]", expect=False)
        rcon("clear Dev", expect=False)
        time.sleep(0.3)

def main():
    print("Dev:", rpc("player.state"))
    for label, etype, nbt in MERCHANTS:
        run_merchant(label, etype, nbt)
    print("\n" + "="*56)
    for n in passed: print("PASS ", n)
    for n in failed: print("FAIL ", n)
    print("="*56)
    print("全部通过" if not failed else f"{len(failed)} 项失败")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
