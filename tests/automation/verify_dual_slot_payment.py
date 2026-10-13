#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交易健壮性：双输入槽支付（单价 >64 走 costB）真机验证。

TradeSpec.toOffer：price>64 时拆 costA=64 + costB=price-64。用 price_overrides
把僵尸腐肉临时定价 100（=64+36），真机走一次成交，断言两槽都被吃、实扣 100、
产物入包、买光售罄。finally 还原远端配置并 reload。

前置：Dev 客户端已连 192.0.2.10。配置经 ssh 改服务端 config/peaceandlove.json。
"""
import subprocess, sys, time, uuid

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

SSH = "mc@192.0.2.10"
CFG = "/home/mc/minecraft/config/peaceandlove.json"
ETYPE = "minecraft:zombie"
KEY = "minecraft:zombie/minecraft:rotten_flesh"
DUAL_PRICE = 100

passed, failed = [], []
def check(name, cond, extra=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + ("  " + str(extra) if extra else ""))
    if not cond: raise AssertionError(name)

def rcon(c, expect=True):
    r = server_rcon(c)
    if expect and any(k in r for k in ("No player","Could not","Failed","Unknown")):
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

def ssh_out(cmd):
    return subprocess.run(["ssh", SSH, cmd], capture_output=True, text=True, timeout=30).stdout

def set_override(add):
    """add=True 设双槽价，False 删除覆盖。"""
    action = (f"po[{KEY!r}]={DUAL_PRICE}" if add else f"po.pop({KEY!r},None)")
    py = (
        "import json\n"
        f"p={CFG!r}\n"
        "d=json.load(open(p))\n"
        "po=d.setdefault('price_overrides',{})\n"
        f"{action}\n"
        "json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)\n"
        "print('rotten_flesh=',d['price_overrides'].get('minecraft:zombie/minecraft:rotten_flesh'))\n"
    )
    r = subprocess.run(["ssh", SSH, "python3 - <<'PY'\n"+py+"PY"], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError("ssh 改配置失败: "+r.stderr)
    print("配置:", r.stdout.strip())

def main():
    print("Dev:", rpc("player.state"))
    tag = "PALD-" + uuid.uuid4().hex[:6]
    # 备份原配置
    backup = ssh_out(f"cp {CFG} /tmp/pal_cfg_backup.json && echo backed-up").strip()
    print(backup)
    try:
        set_override(DUAL_PRICE)
        rcon("pal reload"); time.sleep(1.0)

        IX,IY,IZ=120,-57,60
        # 清同类野生怪，避免 nearestByType 选错目标
        rcon(f"kill @e[type={ETYPE}]",expect=False); time.sleep(0.3)
        rcon(f"tp Dev {IX+0.5} {IY} {IZ+0.5}"); time.sleep(0.3)
        rcon(f"summon {ETYPE} {IX+1} {IY} {IZ} {{NoAI:1b,PersistenceRequired:1b,Tags:[\"{tag}\"]}}")
        time.sleep(0.8)
        rcon("item replace entity Dev weapon.mainhand with air")
        rcon("item replace entity Dev weapon.offhand with air"); time.sleep(0.2)
        try:
            opened=None
            for _ in range(3):
                try:
                    rr=rpc("player.interact",{"target":"zombie","autoClose":False},timeout=15)
                    if rr.get("screenOpen"): opened=rr; break
                except RuntimeError as e:
                    print("  interact 重试:", e)
                time.sleep(1.0)
            check("D1 空手右键开窗", bool(opened), opened)
            rcon("give Dev emerald 128"); time.sleep(0.4)
            st=rpc("trade.status"); offers=st.get("offers",[])
            idx=next((i for i,o in enumerate(offers) if o.get("result")=="minecraft:rotten_flesh"), None)
            check("D2 找到腐肉报价", idx is not None, offers)
            o=offers[idx]
            check("D3 双槽拆分 64+36",
                  o.get("costA")=="minecraft:emerald" and o.get("costACount")==64
                  and o.get("costBCount")==36,
                  {"costA":o.get("costA"),"costACount":o.get("costACount"),
                   "costBCount":o.get("costBCount")})
            before=st.get("inventory",{}).get("minecraft:emerald",0)
            rpc("trade.select",{"index":idx}); time.sleep(0.4)
            st=rpc("trade.status")
            check("D4 select 后结果槽出腐肉", st.get("result",{}).get("item")=="minecraft:rotten_flesh",
                  st.get("result"))
            rpc("trade.take"); time.sleep(0.5)
            st=rpc("trade.status")
            inv_emer=st.get("inventory",{}).get("minecraft:emerald",0)
            # 成交后原版菜单会自动为下一单向货币槽补货（不够整价也会把残量挪进 costA），
            # 故剩余绿宝石 = 背包 + costA 槽 + costB 槽，残量停在货币槽不算被扣。
            def slot_emer(key):
                sl=st.get(key,{})
                return sl.get("count",0) if sl.get("item")=="minecraft:emerald" else 0
            remain=inv_emer+slot_emer("costA")+slot_emer("costB")
            flesh=st.get("inventory",{}).get("minecraft:rotten_flesh",0)
            paid=before-remain
            check("D5 双槽实扣 100 绿宝石", paid==100,
                  {'before':before,'背包':inv_emer,'costA槽':slot_emer("costA"),
                   'costB槽':slot_emer("costB"),'paid':paid})
            check("D6 腐肉入包", flesh>=2, {'rotten_flesh':flesh})
            u=st.get("offers",[{}])[idx].get("uses"); oo=st.get("offers",[{}])[idx].get("outOfStock")
            check("D7 uses=1 且即时售罄", u==1 and oo is True, {'uses':u,'outOfStock':oo})
        finally:
            try: rpc("trade.close",timeout=5)
            except Exception: pass
            time.sleep(0.3)
            rcon(f"kill @e[type={ETYPE},tag={tag}]",expect=False)
            rcon("clear Dev",expect=False); time.sleep(0.3)
    finally:
        # 还原配置 + reload
        ssh_out(f"cp /tmp/pal_cfg_backup.json {CFG}")
        rcon("pal reload", expect=False); time.sleep(0.5)
        print("配置已还原并 reload")

    print("\n"+"="*56)
    for n in passed: print("PASS ",n)
    for n in failed: print("FAIL ",n)
    print("="*56)
    print("全部通过" if not failed else f"{len(failed)} 项失败")
    sys.exit(1 if failed else 0)

if __name__=="__main__":
    main()
