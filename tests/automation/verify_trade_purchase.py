#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-TRADE-005 真机验证：真实成交闭环（客户端真实驱动，非服务端伪造）。

前置：Dev 客户端已启动并连上 192.0.2.10（launch_and_connect.py 后手动 connect，
或用 pal_connect 辅助）。服务端已部署带 notifyTrade 重发包修复的最新 PAL jar；
客户端 run/mods 为带 trade.select/take/status/close 的最新 mc-client-rpc。

链路（全部走原版网络管线）：
  空手右键开窗(player.interact, autoClose=false)
  → 开窗后 RCON 给绿宝石（避免主手持物导致 mobInteract 门控失败）
  → trade.select 0（tryMoveItems 把绿宝石挪入货币槽 + SelectTradePacket，服务端权威）
  → 等结果槽出货
  → trade.take（QUICK_MOVE 结果槽，服务端 MerchantResultSlot.onTake 扣款出货 +
    Merchant#notifyTrade：uses+1，并由我们的修复 sendMerchantOffers 重发售罄状态）
断言：
  A1 开窗成功且有报价
  A2 select 后货币槽放入应付绿宝石、结果槽出货
  A3 take 后：绿宝石实扣==应付、产物入包数量正确、报价 uses+1
  A4 若该报价 maxUses==1：客户端 menu 即时显示售罄（验新增的成交后重发包）
  A5 maxUses==1 时再次 select 无法再成交（限购真生效）

退出码 0=全绿。
"""
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

NAME = "ttrade"
ETYPE = "zombie"
# 与 verify_trade_interaction 一致的固定隔间
IX, IY, IZ = 120, -57, 60
EMERALD = "minecraft:emerald"

results = []


def log(*a):
    print(*a, flush=True)


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    log(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if detail else ""))


def rcon(cmd):
    return server_rcon(cmd)


def status():
    return rpc("trade.status", timeout=8)


def wait_status(pred, timeout=6.0, interval=0.25):
    """轮询 trade.status 直到 pred(st) 为真；返回最后一次 st。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = status()
        if isinstance(last, dict) and pred(last):
            return last
        time.sleep(interval)
    return last


def arena():
    rcon(f"fill {IX-1} {IY-1} {IZ-1} {IX+2} {IY-1} {IZ+1} deepslate")
    rcon(f"fill {IX-1} {IY} {IZ-1} {IX+2} {IY+2} {IZ+1} air")


def count_item(st, key):
    """trade.status 槽/背包里某物品数量。"""
    if not isinstance(st, dict):
        return 0
    return int(st.get("inventory", {}).get(key, 0))


def slot_count(st, slot):
    s = st.get(slot) or {}
    return int(s.get("count", 0)) if s.get("item") else 0


def main():
    st0 = rpc("client.status")
    if not (isinstance(st0, dict) and st0.get("inWorld")):
        sys.exit("客户端未进世界")

    rcon("gamerule doMobSpawning false")
    rcon("effect give Dev resistance 600 1 true")
    rcon(f"kill @e[name={NAME}]")
    # 清背包（含双手），保证开窗时空手
    rcon("clear Dev")
    time.sleep(0.3)
    arena()
    rcon(f"tp Dev {IX+0.5} {IY} {IZ+0.5}")
    time.sleep(0.4)
    rcon(f"summon {ETYPE} {IX+1} {IY} {IZ} "
         f"{{CustomName:'{{\"text\":\"{NAME}\"}}',PersistenceRequired:1b,NoAI:1b}}")
    time.sleep(0.8)

    try:
        # 1) 空手开窗（保持开窗，不要 autoClose）
        opened = None
        for _ in range(3):
            try:
                opened = rpc("player.interact",
                             {"target": ETYPE, "autoClose": False}, timeout=15)
                break
            except RuntimeError as e:
                log("  interact 重试:", e)
                time.sleep(1.0)
        check("A1 右键打开交易界面", bool(opened and opened.get("screenOpen")),
              str(opened))

        # 2) 开窗后再给绿宝石（128 → 自动两格 64，覆盖双槽最高价）
        rcon("give Dev emerald 128")
        time.sleep(0.4)
        st = wait_status(lambda s: count_item(s, EMERALD) >= 128, timeout=4.0)
        emerald_before = count_item(st, EMERALD)
        check("A1b 开窗后绿宝石入包", emerald_before >= 128, f"emerald={emerald_before}")

        offers = st.get("offers", []) if isinstance(st, dict) else []
        check("A1c 报价非空", len(offers) > 0, f"offers={len(offers)}")
        if not offers:
            raise RuntimeError("无报价，后续无法进行")

        # 选第 0 条（僵尸首条通常是便宜的腐肉）
        idx = 0
        target_result = offers[idx].get("result")
        result_count = offers[idx].get("resultCount")
        max_uses = offers[idx].get("maxUses")
        # 真实成交价取报价 cost（getCostA/B），不是货币槽被填入的数量：
        # 客户端 moveFromInventoryToPaymentSlot 会尽量填满一整组(64)，多放的成交后退回。
        due = int(offers[idx].get("costACount", 0)) + int(offers[idx].get("costBCount", 0))
        log(f"  目标报价 idx={idx} result={target_result} x{result_count} "
            f"maxUses={max_uses} 真实价={due} 绿宝石")

        # 3) select：等货币槽放入足够货币 + 结果槽出货
        rpc("trade.select", {"index": idx}, timeout=8)
        pre = wait_status(
            lambda s: slot_count(s, "costA") + slot_count(s, "costB") >= due
            and slot_count(s, "result") > 0,
            timeout=6.0)
        placed = slot_count(pre, "costA") + slot_count(pre, "costB")
        result_ready = slot_count(pre, "result")
        check("A2 select 后货币槽放入足额绿宝石且结果槽出货",
              placed >= due and result_ready == result_count,
              f"放入={placed}(>={due}) 结果槽={pre.get('result')}")

        # 4) take 成交：等产物入包 / uses+1
        rpc("trade.take", timeout=8)
        post = wait_status(
            lambda s: any(o.get("index") == idx and o.get("uses", 0) >= 1
                          for o in s.get("offers", [])),
            timeout=6.0)

        # 实扣 = 初始 - (背包剩余 + 货币槽剩余)。take 只按真实价 shrink，
        # 多放进货币槽的部分仍留在槽里（关窗退回），故把槽内剩余也算作"未扣"。
        paid = emerald_before - (
                count_item(post, EMERALD)
                + slot_count(post, "costA") + slot_count(post, "costB"))
        gained = count_item(post, target_result)
        offer0 = next((o for o in post.get("offers", []) if o.get("index") == idx), {})
        uses = offer0.get("uses")
        out = offer0.get("outOfStock")
        log(f"  成交后: 实扣绿宝石={paid}(应付{due}) 入包 {target_result}={gained}"
            f"(应{result_count}) uses={uses} outOfStock={out}")

        check("A3a 绿宝石实扣==应付", paid == due, f"paid={paid} due={due}")
        check("A3b 产物入包数量正确", gained >= result_count,
              f"{target_result}={gained} 应>={result_count}")
        check("A3c 报价 uses+1", uses == 1, f"uses={uses}")

        # 5) maxUses==1：客户端即时售罄（验新增的成交后重发包），且不能再买
        if max_uses == 1:
            check("A4 成交后客户端即时显示售罄(重发包)", out is True,
                  f"outOfStock={out}")
            # 再次 select：售罄报价拿不到结果（tryMoveItems 即便放入货币，结果槽也不出货）
            rpc("trade.select", {"index": idx}, timeout=8)
            time.sleep(0.8)
            st2 = status()
            blocked = slot_count(st2, "result") == 0
            check("A5 买光后再次 select 无法成交(限购)", blocked,
                  f"结果槽={st2.get('result')} uses={[o.get('uses') for o in st2.get('offers', [])]}")
        else:
            log(f"  (maxUses={max_uses}≠1，跳过售罄/限购断言)")

    finally:
        # 关窗 + 清理（无论成败）
        try:
            rpc("trade.close", timeout=5)
        except Exception:
            pass
        rcon(f"tp Dev {IX+1.5} {IY} {IZ+1.5}")
        rcon(f"kill @e[name={NAME}]")
        rcon("clear Dev")
        log("已关窗并清理测试怪/背包")

    log("\n" + "=" * 56)
    for label, ok in results:
        log("PASS " if ok else "FAIL ", label)
    log("=" * 56)
    if all(ok for _, ok in results):
        log("全部通过")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
