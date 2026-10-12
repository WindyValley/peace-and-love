#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-TRADE-004 真机验证：补货（重置 uses）、小数周期、NBT 持久化、离线补算。

前置：客户端 Dev 已连上 192.0.2.10（launch_and_connect.py）。被测 jar 已部署。

判定全部走服务端：RCON 召唤/改配置 + verify-RPC(25585) trade.probe 读/置 uses。
probe.getOffers() 会触发报价组装（无需真右键）；stock="out" 置满 uses 模拟买光
（真实成交链路属 T-TRADE-005）。

用例：
  A 长周期持久化：interval=1 天，置满 uses → 卸载区块 → 回来 uses 仍=1（购买次数没丢）
  B 短周期在线补货：interval=0.005 天(120t≈6s)，置满 → 原地等 8s → uses=0（在线补货）
  C 短周期离线补算：置满 → 卸载区块并在远处等过周期 → 回来首 tick uses=0（加载时补算）

「卸载」判定：玩家 tp 到 512 格外后，probe 遍历 loaded 实体找不到该怪 = 区块已存盘卸载
（不是没跑）。getGameTime 单调，/time set 不影响（整数天/边界已由 RestockManagerTest 覆盖）。

退出码 0=全绿。
"""
import json
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

SSH_TARGET = "mc@192.0.2.10"
REMOTE_DIR = "/home/mc/minecraft"
CFG = f"{REMOTE_DIR}/config/peaceandlove.json"
PAL_RPC = ("192.0.2.10", 25585)
_id = [200]

results = []
NAME = "rstest"
# 测试平台（主世界固定点）
BX, BY, BZ = 120, -57, 40
FAR_X = BX + 512


def log(*a):
    print(*a, flush=True)


def ssh_run(cmd, timeout=30):
    r = subprocess.run(["ssh", SSH_TARGET, cmd],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.returncode


def set_remote_number(key, value):
    py = (f"import json;p='{CFG}';"
          f"d=json.load(open(p));d['{key}']={value};"
          f"json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)")
    out, rc = ssh_run(f"python3 -c \"{py}\"")
    if rc != 0:
        raise RuntimeError(f"改远端配置失败: {out}")
    server_rcon("pal reload")
    time.sleep(1.0)


def pal(method, params=None):
    _id[0] += 1
    req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": _id[0]}
    s = socket.create_connection(PAL_RPC, timeout=5)
    try:
        s.sendall((json.dumps(req) + "\n").encode())
        s.settimeout(5)
        buf = b""
        while b"\n" not in buf:
            c = s.recv(4096)
            if not c:
                break
            buf += c
        r = json.loads(buf.decode().strip())
        return r.get("result") if "result" in r else r.get("error")
    finally:
        s.close()


def probe(stock=None):
    p = {"name": NAME}
    if stock:
        p["stock"] = stock
    return pal("trade.probe", p)


def parse_uses(r):
    if not isinstance(r, str):
        return None, None
    mu = re.search(r"uses=([0-9/,X]+)", r)
    mg = re.search(r"gameTime=(\d+)", r)
    return (mu.group(1) if mu else None), (int(mg.group(1)) if mg else None)


def parse_field(r, key):
    if not isinstance(r, str):
        return None
    m = re.search(rf"{key}=(-?\d+)", r)
    return int(m.group(1)) if m else None


def all_out(uses):
    return bool(uses) and all(seg.endswith("X") for seg in uses.split(","))


def all_zero(uses):
    return bool(uses) and all(seg.startswith("0/") for seg in uses.split(","))


def setup_mob():
    server_rcon(f"kill @e[name={NAME}]")
    time.sleep(0.3)
    # 平台与 2 格高空间
    server_rcon(f"fill {BX-1} {BY-1} {BZ-1} {BX+1} {BY-1} {BZ+1} deepslate")
    server_rcon(f"fill {BX-1} {BY} {BZ-1} {BX+1} {BY+2} {BZ+1} air")
    # 远处落脚点（防悬空/防摔）
    server_rcon(f"fill {FAR_X-1} {BY-1} {BZ-1} {FAR_X+1} {BY-1} {BZ+1} deepslate")
    server_rcon(f"fill {FAR_X-1} {BY} {BZ-1} {FAR_X+1} {BY+2} {BZ+1} air")
    server_rcon(f"summon zombie {BX+0.5} {BY} {BZ+0.5} "
                f"{{CustomName:'{{\"text\":\"{NAME}\"}}',PersistenceRequired:1b,NoAI:1b}}")
    time.sleep(0.6)
    r = probe()
    log("  探针:", r)
    return r


def unload_and_wait():
    """tp 玩家到远处，轮询直到怪从 loaded 实体消失（区块已卸载存盘）。"""
    server_rcon(f"tp Dev {FAR_X+0.5} {BY} {BZ+0.5}")
    t = time.time()
    while time.time() - t < 40:
        r = probe()
        if isinstance(r, str) and "找不到" in r:
            return True
        time.sleep(1.0)
    return False


def come_back(wait_loaded=12):
    server_rcon(f"tp Dev {BX+1.5} {BY} {BZ+1.5}")
    t = time.time()
    while time.time() - t < wait_loaded:
        r = probe()
        if isinstance(r, str) and "找不到" not in r:
            time.sleep(0.6)  # 给加载后首 tick 补货判定留时间
            return r
        time.sleep(0.5)
    return probe()


def check(label, ok, detail=""):
    results.append((label, ok))
    log(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if detail else ""))


def main():
    st = rpc("client.status")
    if not (isinstance(st, dict) and st.get("inWorld")):
        sys.exit("客户端未进世界，先跑 launch_and_connect.py")

    server_rcon("gamerule doMobSpawning false")
    server_rcon("effect give Dev resistance 600 1 true")
    set_remote_number("restock_interval_days", 1)
    try:
        # ── 用例 A：长周期持久化（卸载/重挂不丢购买次数）──
        log("\n--- A: interval=1天，置满→卸载→回来 uses 应保留=1 ---")
        setup_mob()
        r = probe(stock="out")
        uses, gt = parse_uses(r)
        log(f"  置满后 uses={uses} gameTime={gt}")
        check("A1 置满成功", all_out(uses), uses or str(r))
        unloaded = unload_and_wait()
        check("A2 区块确实卸载(怪从loaded消失)", unloaded)
        time.sleep(1.0)
        r = come_back()
        uses, gt2 = parse_uses(r)
        log(f"  回来后 uses={uses} gameTime={gt2}（推进 {None if gt is None else gt2-gt}）")
        check("A3 持久化：跨卸载购买次数保留(仍售罄)", all_out(uses), uses or str(r))

        # ── 用例 B：短周期在线补货 ──
        log("\n--- B: interval=0.005天(120t≈6s)，置满→原地等 8s → uses=0 ---")
        set_remote_number("restock_interval_days", 0.005)
        time.sleep(0.5)
        r = probe(stock="out")
        uses, gt = parse_uses(r)
        log(f"  置满后 uses={uses} gameTime={gt}")
        check("B1 置满成功", all_out(uses), uses or str(r))
        time.sleep(8.0)
        r = probe()
        uses, gt2 = parse_uses(r)
        log(f"  8s 后 uses={uses} gameTime={gt2}（推进 {None if gt is None else gt2-gt} tick）")
        check("B2 在线小数周期补货(uses 归零)", all_zero(uses), uses or str(r))

        # ── 用例 C：短周期离线补算（卸载期间跨周期，加载首 tick 清零）──
        log("\n--- C: 置满→卸载并在远处等过周期→回来 uses=0（加载时补算）---")
        r = probe(stock="out")
        uses, gt = parse_uses(r)
        log(f"  置满后 uses={uses} gameTime={gt}")
        check("C1 置满成功", all_out(uses), uses or str(r))
        unloaded = unload_and_wait()
        check("C2 区块确实卸载", unloaded)
        # 卸载状态下在远处多等，让世界时钟跨过 120t 周期（实体本身冻结不 tick）
        time.sleep(10.0)
        r = come_back()
        uses, gt2 = parse_uses(r)
        log(f"  回来后 uses={uses} gameTime={gt2}（推进 {None if gt is None else gt2-gt} tick）")
        check("C3 离线跨周期加载时补算(uses 归零)", all_zero(uses), uses or str(r))

        # ── 用例 D：睡觉腿（getDayTime 跨自然日），滚动间隔远未到 ──
        # /time add 24000 只走 setDayTime（源码 TimeCommand.addTime 证实），与玩家睡觉醒来
        # 的快进是同一条路径；它不碰单调的 getGameTime。interval=1 天(24000t)，
        # gameTime 只前进几十 tick，却因自然日 +1 触发补货——专测对齐村民的第二条腿。
        log("\n--- D: interval=1天，置满→/time add 24000(仅跨天,不碰gameTime)→ uses 应归零 ---")
        set_remote_number("restock_interval_days", 1)
        setup_mob()
        r = probe(stock="out")
        uses, gt0 = parse_uses(r)
        day0 = parse_field(r, "day")
        log(f"  置满后 uses={uses} gameTime={gt0} day={day0}")
        check("D1 置满成功", all_out(uses), uses or str(r))
        server_rcon("time add 24000")
        time.sleep(1.2)  # 让实体跑若干 tick，触发 tick HEAD 的双时钟判定
        r = probe()
        uses, gt1 = parse_uses(r)
        day1 = parse_field(r, "day")
        gdelta = None if (gt0 is None or gt1 is None) else gt1 - gt0
        log(f"  跨天后 uses={uses} gameTime={gt1}(+{gdelta}) day={day0}->{day1}")
        check("D2 跨自然日(睡觉路径)补货,uses 归零", all_zero(uses), uses or str(r))
        check("D3 确实只跨天:gameTime 推进远<24000 且 day+1",
              gdelta is not None and 0 <= gdelta < 24_000 and day1 is not None
              and day0 is not None and day1 == day0 + 1,
              f"gameTime+{gdelta}, day {day0}->{day1}")
    finally:
        server_rcon(f"tp Dev {BX+1.5} {BY} {BZ+1.5}")
        server_rcon(f"kill @e[name={NAME}]")
        set_remote_number("restock_interval_days", 1)
        log("\n已还原 restock_interval_days=1 并清理测试怪")

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
