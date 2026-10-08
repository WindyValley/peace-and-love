#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C 类直调示警验证（guardian）——判定走 PAL 自带 JSON-RPC 的 mob.anger 探针。

为什么不用 getTarget() marker 通道：守卫者 GuardianAttackGoal 每 tick
做视线校验，陆地隔间里会立刻 setTarget(null)，原版目标读不到；
但 mod 的 AngerSource（PLAYER_DIRECT/KIN_ALERT）自管、保留 30s。

封闭几何（东西向，z 宽 1 格）：
  西墙 玩家间 窗 target间 墙 near全封      far全封
  [S]  [P]   ║ [G]    [S] [G]            [G]
       px         px+1     px+3          px+9
target↔near≈2(<4)  target↔far≈8(>4)
玩家封在 1x1x2 隔间仅朝东留 1x2 攻击窗，距离锁死 ~1 格。

预期：target=PLAYER_DIRECT  near=KIN_ALERT  far=NONE
用法：python verify_alert_guardian_v2.py [guardian|elder_guardian]
"""
import json
import re
import socket
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon

TYPE = sys.argv[1] if len(sys.argv) > 1 else "guardian"
EXTRA = sys.argv[2] if len(sys.argv) > 2 else ""    # 如 '{Size:2}'
NEAR_CELL, FAR_CELL = 3, 9
PAL_RPC = ("192.0.2.10", 25585)
_id = [0]


def log(*a):
    print(*a, flush=True)


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


def anger_source(name):
    r = pal("mob.anger", {"name": name})
    if not isinstance(r, str) or "source=" not in r:
        return None, r
    m = re.search(r"source=(\w+);target=([\w]+)", r)
    return (m.group(1), m.group(2)) if m else (None, r)


def player_xyz():
    # 新协议：player.pos 返回结构化 dict {x,y,z,...}（float）
    p = rpc("player.pos")
    return float(p["x"]), float(p["y"]), float(p["z"])


def hp(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] Health")
    m = re.search(r"([\d.]+)f?", out)
    return float(m.group(1)) if m else None


def pos(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] Pos")
    m = re.search(r"\[([-\d.]+)d,\s*([-\d.]+)d,\s*([-\d.]+)d\]", out)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3))) if m else None


def fill(a, b, block="stone"):
    server_rcon(f"fill {a} {b} {block}")


def build_cell(x, iy, iz):
    """怪隔间：3x2x3 石壳，中心仅 1 格高（守卫者0.85/小史莱姆0.52 放得下，跳不起、漂不动）。"""
    fill(f"{x-1} {iy-1} {iz-1}", f"{x+1} {iy+1} {iz+1}")
    fill(f"{x} {iy} {iz}", f"{x} {iy} {iz}", "air")


def summon(name, x, iy, iz):
    extra = ("," + EXTRA[1:-1]) if EXTRA else ""
    # NoAI:1b：怪物不动不漂不窒息，几何精确、attackNearest 稳定命中。
    # anger 标记存在 AngerController 的 map，setTarget 是字段，均与 AI 是否运行无关。
    server_rcon(f"summon {TYPE} {x} {iy} {iz} "
                f"{{CustomName:'{{\"text\":\"{name}\"}}',PersistenceRequired:1b,NoAI:1b{extra}}}")


def do_attack(target, tries=3):
    """player.attackNearest：新协议成功返回结构化对象，错误 raise。
    超距(-32003)/忙(-32004) 可重试；其他错误直接抛。"""
    last = None
    for i in range(tries):
        try:
            return rpc("player.attackNearest", {"target": target})
        except RuntimeError as e:
            last = e
            msg = str(e)
            if "[-32003]" in msg or "[-32004]" in msg:
                time.sleep(1.5 * (i + 1))
                continue
            raise
    raise last


def main():
    # 新协议：player.state 返回 dict，死亡看 st['dead']
    state = rpc("player.state")
    if state["dead"]:
        rpc("player.respawn")
        time.sleep(2)
    server_rcon("gamerule doMobSpawning false")
    server_rcon("kill @e[type=!player,distance=..80]")
    server_rcon("kill @e[type=marker]")
    for n in ("target", "near", "far"):
        server_rcon(f"kill @e[name={n}]")
    time.sleep(1)

    sx, sy, sz = player_xyz()
    ix, iy, iz = int(round(sx)), int(round(sy)), int(round(sz))
    log(f"=== {TYPE} {EXTRA} === 台心 ({ix},{iy},{iz})")

    # 建造范围：x ix-2..ix+11（far 壳在 ix+9，外壁到 ix+10），y iy-2..iy+3，z iz-2..iz+2
    X0, X1, Y0, Y1, Z0, Z1 = ix - 2, ix + 11, iy - 2, iy + 3, iz - 2, iz + 2

    try:
        # 0) 先把玩家移到盒外东侧临时点并垫脚，再清空建造盒（消除历轮残留石结构）
        server_rcon(f"tp Dev {ix+12}.5 {iy} {iz+0.5}")
        server_rcon(f"fill {ix+11} {iy-1} {iz-1} {ix+13} {iy-1} {iz+1} stone")
        time.sleep(0.5)
        server_rcon(f"fill {X0} {Y0} {Z0} {X1} {Y1} {Z1} air")

        # 1) 玩家+target 连体壳，near/far 全封
        fill(f"{ix-1} {iy-1} {iz-1}", f"{ix+2} {iy+2} {iz+1}")
        fill(f"{ix} {iy} {iz}", f"{ix+1} {iy+1} {iz}", "air")
        build_cell(ix + NEAR_CELL, iy, iz)
        build_cell(ix + FAR_CELL, iy, iz)
        server_rcon(f"tp Dev {ix+0.5} {iy} {iz+0.5}")
        time.sleep(1.0)
        server_rcon("effect give Dev instant_health 2 10 true")
        server_rcon("effect give Dev resistance 30 1 true")

        summon("target", ix + 1, iy, iz)
        summon("near", ix + NEAR_CELL, iy, iz)
        summon("far", ix + FAR_CELL, iy, iz)
        time.sleep(1.5)

        tp, np_ = pos("target"), pos("near")
        log(f"  target={tp} HP={hp('target')}")
        log(f"  near={np_} HP={hp('near')}  farHP={hp('far')}")
        d = ((tp[0]-np_[0])**2 + (tp[2]-np_[2])**2) ** 0.5
        log(f"  target↔near={d:.2f}（应≈2,<4）")

        for n in ("target", "near", "far"):
            log(f"  攻击前 {n}: {anger_source(n)}")

        hp0 = hp("target")
        res = do_attack(TYPE)
        log("attackNearest ->", f"hit={res['hit']} dist={res['distance']} reach={res['reach']} "
            f"hp {res['hpBefore']}->{res['hpAfter']}")
        time.sleep(1.0)
        hp1 = hp("target")

        t_src, t_tgt = anger_source("target")
        n_src, n_tgt = anger_source("near")
        f_src, f_tgt = anger_source("far")
        log(f"攻击后 targetHP {hp0}->{hp1}")
        log(f"  target: source={t_src} target={t_tgt}（source 应 PLAYER_DIRECT）")
        log(f"  near:   source={n_src} target={n_tgt}（source 应 KIN_ALERT）")
        log(f"  far:    source={f_src} target={f_tgt}（source 应 NONE）")

        # target 可能被一拳打死（如 Size:1 史莱姆）：hurt HEAD 的示警在死亡前已分发，
        # near 的 KIN_ALERT 标记不依赖 target 存活。target 查询缺失时以 near/far 为准。
        target_died = hp1 is None
        t_ok = t_src == "PLAYER_DIRECT" or (t_src is None and target_died)
        ok = (t_ok and n_src == "KIN_ALERT" and f_src == "NONE")
        note = "，target 一击死亡但示警已在死前分发" if target_died and t_src is None else ""
        log("结果:", "✅ PASS（%s：near 被同族示警、far 不示警%s）" % (TYPE, note)
            if ok else "❌ FAIL")
        sys.exit(0 if ok else 1)
    finally:
        for n in ("target", "near", "far"):
            server_rcon(f"kill @e[name={n}]")
        server_rcon("kill @e[type=marker]")
        # 西侧落脚平台 → 送玩家过去 → 拆整个建造盒
        server_rcon(f"fill {X0} {iy-1} {iz-1} {ix-2} {iy-1} {iz+1} stone")
        server_rcon(f"tp Dev {X0+0.5} {iy} {iz+0.5}")
        time.sleep(0.5)
        server_rcon(f"fill {X0} {Y0} {Z0} {X1} {Y1} {Z1} air")
        # 落脚平台最后补回（清盒时被一起清掉）
        server_rcon(f"fill {X0} {iy-1} {iz-1} {ix-2} {iy-1} {iz+1} stone")
        server_rcon("gamerule doMobSpawning true")


if __name__ == "__main__":
    main()
