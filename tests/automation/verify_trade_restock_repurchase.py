#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-TRADE-005 补充：买光 → 睡觉腿补货 → 重开窗口 → 再次真实购买（004+005 端到端串联）。

前置同 verify_trade_purchase.py。一次给 128 绿宝石足够买两次（单价 16）。
补货用 /time add 24000（只快进 getDayTime、与睡觉同路径），interval=1 天即触发。
补货发生在实体 tick（resetUses），不主动推 GUI（同原版村民），故关窗后重开拿新报价。
退出码 0=全绿。
"""
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

NAME = "ttraderr"
ETYPE = "zombie"
IX, IY, IZ = 120, -57, 80
EMERALD = "minecraft:emerald"
results = []


def log(*a):
    print(*a, flush=True)


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    log(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if detail else ""))


def rcon(c):
    return server_rcon(c)


def status():
    return rpc("trade.status", timeout=8)


def slot(st, k):
    s = st.get(k) or {}
    return int(s.get("count", 0)) if s.get("item") else 0


def inv(st, key):
    return int(st.get("inventory", {}).get(key, 0))


def wait_s(pred, timeout=6.0):
    dl = time.time() + timeout
    last = None
    while time.time() < dl:
        last = status()
        if isinstance(last, dict) and pred(last):
            return last
        time.sleep(0.25)
    return last


def open_menu():
    last = None
    for _ in range(3):
        try:
            r = rpc("player.interact", {"target": ETYPE, "autoClose": False}, timeout=15)
            last = r
            if r.get("screenOpen"):
                return r
        except RuntimeError as e:
            last = {"exception": str(e)}
            log("  interact 重试:", e)
        time.sleep(1.0)
    raise RuntimeError("开窗失败: " + repr(last))


def buy_once(idx, result_key, tag):
    """select + take，返回成交后 status。要求结果槽出货且成交后该 offer uses>=1。"""
    rpc("trade.select", {"index": idx}, timeout=8)
    pre = wait_s(lambda s: slot(s, "result") > 0)
    ok_ready = slot(pre, "result") > 0
    check(f"{tag}-1 select 后结果槽出货", ok_ready, str(pre.get("result")))
    rpc("trade.take", timeout=8)
    post = wait_s(lambda s: any(o.get("index") == idx and o.get("uses", 0) >= 1
                                for o in s.get("offers", [])))
    o = next((x for x in post.get("offers", []) if x.get("index") == idx), {})
    check(f"{tag}-2 take 成交 uses+1", o.get("uses") == 1 and inv(post, result_key) > 0,
          f"uses={o.get('uses')} {result_key}={inv(post, result_key)}")
    return post


def main():
    st = rpc("client.status")
    if not (st.get("inWorld")):
        sys.exit("客户端未进世界")
    rcon("gamerule doMobSpawning false")
    rcon("effect give Dev resistance 600 1 true")
    rcon(f"kill @e[name={NAME}]")
    rcon("clear Dev")
    time.sleep(0.3)
    rcon(f"fill {IX-1} {IY-1} {IZ-1} {IX+2} {IY-1} {IZ+1} deepslate")
    rcon(f"fill {IX-1} {IY} {IZ-1} {IX+2} {IY+2} {IZ+1} air")
    rcon(f"tp Dev {IX+0.5} {IY} {IZ+0.5}")
    time.sleep(0.4)
    rcon(f"summon {ETYPE} {IX+1} {IY} {IZ} "
         f"{{CustomName:'{{\"text\":\"{NAME}\"}}',PersistenceRequired:1b,NoAI:1b}}")
    time.sleep(0.8)

    try:
        check("S0 开窗", bool(open_menu().get("screenOpen")))
        rcon("give Dev emerald 128")
        st = wait_s(lambda s: inv(s, EMERALD) >= 128, timeout=4.0)
        offers = st.get("offers", [])
        idx = 0
        result_key = offers[idx]["result"]
        due = int(offers[idx].get("costACount", 0)) + int(offers[idx].get("costBCount", 0))
        log(f"  报价0: {result_key} 真实价={due}")

        # 第一次买 → 售罄
        post1 = buy_once(idx, result_key, "B1")
        o1 = next(x for x in post1["offers"] if x["index"] == idx)
        check("B1-3 买光后售罄", o1.get("outOfStock") is True, f"uses={o1.get('uses')}")
        flesh_after1 = inv(post1, result_key)
        em_after1 = inv(post1, EMERALD) + slot(post1, "costA") + slot(post1, "costB")
        log(f"  第一次后: 腐肉={flesh_after1} 绿宝石剩余(含槽)={em_after1}")

        # 睡觉腿补货（interval=1 天，跨自然日即触发；前提有售罄报价）
        rcon("time add 24000")
        time.sleep(1.5)  # 让实体跑 tick 触发双时钟判定 resetUses

        # 补货不主动推 GUI（同原版村民），关窗再重开拿补货后报价。
        rpc("trade.close", timeout=5)
        time.sleep(0.8)
        # 右键门控要求双手空手（003 设计，区别于村民可持币交易）：买完关窗后服务端把
        # 货币槽剩余绿宝石 placeItemBackInInventory 退回，可能落在主手或副手任一选中/空位，
        # 故主副手都清空（背包其余绿宝石保留，不足再补）。
        rcon("item replace entity Dev weapon.mainhand with air")
        rcon("item replace entity Dev weapon.offhand with air")
        time.sleep(0.3)
        try:
            check("S1 补货后重开窗", bool(open_menu().get("screenOpen")))
        except RuntimeError as e:
            log("  重开窗诊断:", e)
            raise
        st2 = wait_s(lambda s: s.get("offerCount", 0) > 0)
        # 清主手可能清掉一组绿宝石，不足则补足，保证第二次购买有钱。
        if inv(st2, EMERALD) + slot(st2, "costA") + slot(st2, "costB") < due:
            rcon(f"give Dev emerald {due}")
            st2 = wait_s(lambda s: inv(s, EMERALD) >= due, timeout=4.0)
        o2 = next(x for x in st2["offers"] if x["index"] == idx)
        check("B2-0 重开后报价已补货(uses 归零、不再售罄)",
              o2.get("uses") == 0 and o2.get("outOfStock") is False,
              f"uses={o2.get('uses')} out={o2.get('outOfStock')}")

        # 第二次真实购买
        post2 = buy_once(idx, result_key, "B2")
        flesh_after2 = inv(post2, result_key)
        check("B2-3 补货后再次真实成交，产物翻倍",
              flesh_after2 == flesh_after1 + int(offers[idx]["resultCount"]),
              f"腐肉 {flesh_after1}->{flesh_after2}")
        o3 = next(x for x in post2["offers"] if x["index"] == idx)
        check("B2-4 再次买光后又售罄(限购按新周期重新计)", o3.get("outOfStock") is True,
              f"uses={o3.get('uses')}")
    finally:
        try:
            rpc("trade.close", timeout=5)
        except Exception:
            pass
        rcon(f"tp Dev {IX+1.5} {IY} {IZ+1.5}")
        rcon(f"kill @e[name={NAME}]")
        rcon("clear Dev")
        log("已清理")

    log("\n" + "=" * 56)
    for label, ok in results:
        log("PASS " if ok else "FAIL ", label)
    log("=" * 56)
    sys.exit(0 if all(ok for _, ok in results) else 1)


if __name__ == "__main__":
    main()
