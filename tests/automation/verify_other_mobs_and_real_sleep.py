#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双端补充真机：① 非僵尸适配怪种成交（goal+brain 两类）② 真人上床过夜触发补货。

① 怪种：skeleton/creeper/spider/blaze（Goal 系）+ zoglin（Brain 系，主世界不转化），
   各自空手开窗→给币→选第一条报价→take，断言扣款、产物入包、uses=1、即时售罄。
② 真人睡眠：买光一只僵尸→在怪 24 格外放真床（避开 BedBlock 8 格敌怪校验）→
   time set night → player.useBed 真实右键床（非 /time 模拟）→轮询 Sleeping=1→
   等游戏加速到次日早晨→重开窗口断言 uses 归零→再买。

前置：对应平台的客户端已连服（NeoForge:25565 或 Fabric:25566）。
RCON 端口由环境变量 PAL_RCON_PORT 覆盖（fabric runner 用 25576）。
"""
import os
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402
import combat_loop_test  # noqa: E402

_rport = int(os.environ.get("PAL_RCON_PORT", "25575"))
combat_loop_test.SERVER_RCON_PORT = _rport

results = []
def log(*a): print(*a, flush=True)
def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    log(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not ok: raise AssertionError(label)

def rcon(cmd): return server_rcon(cmd)

IX, IY, IZ = 120, -57, 60

def arena():
    rcon(f"fill {IX-1} {IY-1} {IZ-1} {IX+2} {IY-1} {IZ+1} deepslate")
    rcon(f"fill {IX-1} {IY} {IZ-1} {IX+2} {IY+3} {IZ+1} air")

def empty_hands():
    rcon("item replace entity Dev weapon.mainhand with air")
    rcon("item replace entity Dev weapon.offhand with air")
    time.sleep(0.2)

def open_trade(tkey):
    for _ in range(3):
        try:
            r = rpc("player.interact", {"target": tkey, "autoClose": False}, timeout=15)
            if r.get("screenOpen"):
                return r
        except RuntimeError as e:
            log("  interact 重试:", e)
        time.sleep(1.0)
    return None

def count(st, key):
    return int((st.get("inventory") or {}).get(key, 0)) if isinstance(st, dict) else 0

def trade_one_mob(tkey, display):
    """召唤一只 NoAI 怪，真实成交其第一条报价，断言扣款/入包/uses/售罄。"""
    log(f"\n----- 怪种成交：{display} ({tkey}) -----")
    rcon(f"kill @e[type=minecraft:{tkey}]", )
    time.sleep(0.2)
    rcon(f"tp Dev {IX+0.5} {IY} {IZ+0.5}")
    time.sleep(0.2)
    rcon(f"summon minecraft:{tkey} {IX+1} {IY} {IZ} {{NoAI:1b,PersistenceRequired:1b}}")
    time.sleep(0.8)
    empty_hands()
    try:
        opened = open_trade(tkey)
        check(f"[{display}] 右键开窗", bool(opened), opened)
        rcon("give Dev emerald 128"); time.sleep(0.4)
        st = rpc("trade.status", timeout=8)
        offers = st.get("offers", [])
        check(f"[{display}] 有报价", len(offers) > 0, offers)
        if not offers:
            return
        o = offers[0]
        idx = o["index"]; item = o["result"]
        due = int(o.get("costACount", 0)) + int(o.get("costBCount", 0))
        before_emer = count(st, "minecraft:emerald")
        before_item = count(st, item)
        rpc("trade.select", {"index": idx}, timeout=8); time.sleep(0.5)
        rpc("trade.take", timeout=8); time.sleep(0.6)
        post = rpc("trade.status", timeout=8)
        # 剩余绿宝石含货币槽残量
        def slot(k):
            s = post.get(k) or {}
            return int(s.get("count", 0)) if s.get("item") == "minecraft:emerald" else 0
        remain = count(post, "minecraft:emerald") + slot("costA") + slot("costB")
        paid = before_emer - remain
        got = count(post, item) - before_item
        uses = post.get("offers", [{}])[idx].get("uses")
        oo = post.get("offers", [{}])[idx].get("outOfStock")
        check(f"[{display}] 实扣==报价({due})", paid == due,
              f"paid={paid} due={due} 产物={item}x{got} uses={uses}")
        check(f"[{display}] 产物入包", got >= int(o.get("resultCount", 1)), f"{item} +{got}")
        check(f"[{display}] uses=1 且即时售罄", uses == 1 and oo is True, f"uses={uses}")
    finally:
        try: rpc("trade.close", timeout=5)
        except Exception: pass
        time.sleep(0.2)
        rcon(f"kill @e[type=minecraft:{tkey}]")
        rcon("clear Dev")
        time.sleep(0.3)

# ── 真人上床过夜补货 ────────────────────────────────────────────────
# 床在怪南侧 24 格（仍在 simulation distance 内、怪持续 tick，但超出睡觉 8 格敌怪校验）。
BED_FOOT = (IX, IY - 1, IZ + 24)
BED_HEAD = (IX, IY - 1, IZ + 25)   # facing=south → 头枕在 +z
BED_STAND = (IX + 0.5, IY, IZ + 26)

def place_bed():
    fx, fy, fz = BED_FOOT; hx, hy, hz = BED_HEAD
    # 床区与玩家站位铺一条地板（y=IY-1），再清空上方
    rcon(f"fill {IX-1} {IY-1} {IZ+23} {IX+1} {IY-1} {IZ+27} deepslate")
    rcon(f"fill {IX-1} {IY} {IZ+23} {IX+1} {IY+2} {IZ+27} air")
    # 床两格覆盖地板（facing=south：foot 在北 z84，head 在南 z85）
    rcon(f"setblock {fx} {fy} {fz} red_bed[facing=south,part=foot]")
    rcon(f"setblock {hx} {hy} {hz} red_bed[facing=south,part=head]")

def remove_bed():
    fx, fy, fz = BED_FOOT; hx, hy, hz = BED_HEAD
    # 床两格还原成地板，其余地板保留（下次 fill 会覆盖）
    rcon(f"setblock {fx} {fy} {fz} deepslate")
    rcon(f"setblock {hx} {hy} {hz} deepslate")

def sleeping():
    """玩家是否已上床：读服务端 SleepTimer（入睡倒计时 tick，上床后 >0，过夜醒来归 0）。
    Bed/SleepingPos 字段 data get 读不到；SleepTimer 实测 11→101→0（~5s 过夜）是可靠判据。"""
    out = rcon("data get entity Dev SleepTimer")
    seg = out.split("data:")[-1].strip().replace("s", "")
    try:
        return int(seg) > 0, out.strip()
    except ValueError:
        return False, out.strip()

def time_of_day():
    out = rcon("time query daytime")
    # "The current time of day is 13000"
    try: return int(out.strip().split()[-1])
    except Exception: return -1

def day():
    out = rcon("time query day")
    try: return int(out.strip().split()[-1])
    except Exception: return -1

def real_sleep_restock():
    log("\n----- 真人上床过夜触发补货 -----")
    rcon("gamerule playersSleepingPercentage 0")
    rcon("gamerule doMobSpawning false")
    arena()
    # 关键：必须在怪首次开窗(getOffers 锚定补货自然日)之前把时间设到夜晚，
    # 这样怪的补货日锚点=今夜(day 0)；买光后真人睡觉快进到次日清晨(getDayTime
    # 跨过 24000 → day 1)，相对锚点自然日 +1，才会触发跨日补货腿。
    # 若开窗后才 time set night 会把 getDayTime 往回拨，睡觉后相对锚点不增、不补货。
    rcon("time set 13000")
    time.sleep(0.4)
    # 专属交易怪（僵尸），买光
    rcon("kill @e[type=minecraft:zombie]"); time.sleep(0.2)
    rcon(f"tp Dev {IX+0.5} {IY} {IZ+0.5}"); time.sleep(0.2)
    rcon(f"summon minecraft:zombie {IX+1} {IY} {IZ} {{NoAI:1b,PersistenceRequired:1b,Tags:[\"sleepz\"]}}")
    time.sleep(0.8)
    empty_hands()
    try:
        opened = open_trade("zombie")
        check("[睡眠] 开窗买光", bool(opened), opened)
        rcon("give Dev emerald 128"); time.sleep(0.4)
        st = rpc("trade.status", timeout=8); offers = st["offers"]
        idx = 0; item = offers[0]["result"]
        rpc("trade.select", {"index": idx}, timeout=8); time.sleep(0.5)
        rpc("trade.take", timeout=8); time.sleep(0.6)
        st = rpc("trade.status", timeout=8)
        check("[睡眠] 买光 uses=1 售罄",
              st["offers"][idx]["uses"] == 1 and st["offers"][idx]["outOfStock"],
              st["offers"][idx])
        # 关窗，去床边
        rpc("trade.close", timeout=5); time.sleep(0.4)
        empty_hands()
        place_bed()
        rcon(f"tp Dev {BED_STAND[0]} {BED_STAND[1]} {BED_STAND[2]} facing {BED_HEAD[0]+0.5} {BED_HEAD[1]} {BED_HEAD[2]+0.5}")
        time.sleep(0.5)
        # 床的"8 格内有敌怪不能睡"判定以玩家为中心。围绕玩家清 16 格内所有实体，
        # 但保留 24 格外的交易怪（继续 tick 触发跨自然日补货）。必须 execute at Dev：
        # RCON 命令原点是世界出生点，裸 distance 选择器不围着玩家。
        rcon("execute as Dev at Dev run kill @e[type=!minecraft:player,distance=..16]")
        time.sleep(0.4)
        tod0 = time_of_day()
        # 怪距床的水平距离
        log(f"  睡前 daytime={tod0}（怪在 24 格外加载中、不挡睡）")
        hx, hy, hz = BED_HEAD
        bed_r = rpc("player.useBed", {"x": hx, "y": hy, "z": hz}, timeout=8)
        log("  useBed:", bed_r)
        # 轮询确认真的睡着（Bed 坐标非空），而非被拒
        slept = False; bed_dbg = ""
        for _ in range(12):
            slept, bed_dbg = sleeping()
            if slept: break
            time.sleep(0.5)
        check("[睡眠] 真人成功上床(SleepTimer>0)", slept, bed_dbg)
        # 等过夜并自然醒来：睡前在夜(tod>=12540)，睡后 getDayTime 跳到次日清晨
        # （daytime 回卷到 <2345、SleepTimer 归 0）。注意不能用 `time query day`——
        # 它是单调 gameTime/24000，玩家睡觉只推进 getDayTime 不推进 gameTime（query day 不变），
        # 而 PAL 补货跨日腿恰恰用 getDayTime()/24000，所以 daytime 回卷才是正确判据。
        crossed = False
        for i in range(40):
            tod = time_of_day()
            sleeping_now, _ = sleeping()
            if tod < 2345 and tod0 >= 12540 and not sleeping_now:
                crossed = True
                break
            time.sleep(1.0)
        check("[睡眠] 睡过夜晚进入次日清晨(daytime 夜→晨回卷)",
              crossed, f"tod {tod0}->{time_of_day()} SleepTimer={sleeping()[1].split('data:')[-1].strip()}")
        # 醒来后回怪处，重开窗口，uses 应已由跨自然日补货归零
        time.sleep(1.0)
        rcon(f"tp Dev {IX+0.5} {IY} {IZ+0.5}"); time.sleep(0.5)
        empty_hands()
        opened = open_trade("zombie")
        check("[睡眠] 补货后重开窗", bool(opened), opened)
        st = rpc("trade.status", timeout=8)
        o = st["offers"][idx]
        check("[睡眠] 睡觉腿补货 uses 归零、不再售罄",
              o["uses"] == 0 and not o["outOfStock"], o)
        # 再买一次，产物翻倍
        before_item = count(st, item)
        rpc("trade.select", {"index": idx}, timeout=8); time.sleep(0.5)
        rpc("trade.take", timeout=8); time.sleep(0.6)
        st = rpc("trade.status", timeout=8)
        got = count(st, item) - before_item
        check("[睡眠] 睡觉补货后能再次真买", got >= 1 and st["offers"][idx]["uses"] == 1,
              f"{item} +{got}")
    finally:
        try: rpc("trade.close", timeout=5)
        except Exception: pass
        remove_bed()
        rcon("kill @e[tag=sleepz]")
        rcon("kill @e[type=minecraft:zombie]")
        rcon("clear Dev")
        rcon("gamerule playersSleepingPercentage 100")
        time.sleep(0.3)

def main():
    st0 = rpc("client.status")
    if not (isinstance(st0, dict) and st0.get("inWorld")):
        sys.exit("客户端未进世界")
    rcon("effect give Dev resistance 600 1 true")
    rcon("gamerule doMobSpawning false")
    # ① 多怪种（goal + brain）
    for tkey, disp in [
        ("skeleton", "骷髅/Goal"),
        ("creeper", "苦力怕/Goal"),
        ("spider", "蜘蛛/Goal"),
        ("blaze", "烈焰人/Goal"),
        ("zoglin", "僵尸疣猪兽/Brain"),
    ]:
        trade_one_mob(tkey, disp)
    # ② 真人睡觉
    real_sleep_restock()

    log("\n" + "=" * 60)
    bad = 0
    for label, ok in results:
        log("PASS " if ok else "FAIL ", label)
        bad += 0 if ok else 1
    log("=" * 60)
    log("全部通过" if bad == 0 else f"{bad} 项失败")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
