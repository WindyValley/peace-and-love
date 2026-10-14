#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-NEUT-005 真机：幻翼（phantom）。

源码前提（已核对 mc-1.21.1-sources）：
  - registerGoals: targetSelector 唯一索敌 PhantomAttackPlayerTargetGoal
    （裸 Goal，非 TargetGoal），canUse 只看 range+isAttackable，**不看 insomnia**，
    扫到玩家就 setTarget。中立化谓词收窄后它应被删除 → 幻翼永不主动 setTarget →
    PhantomAttackStrategyGoal/SweepAttackGoal.canUse 要求 getTarget()!=null → 不俯冲。
  - 幻翼**无 HurtByTargetGoal**。玩家打它的反击全靠 mod 的
    LivingEntityHurtMixin → AngerController.onPlayerAttack（对所有中立化 Mob 通用
    setTarget(attacker)），打后攻击策略 goal 启动、俯冲反击。
  - phantom 默认在 hostile_whitelist（保持原版敌对），验前必须先 remove。

两阶段（夜晚，开阔平台，不用 NoAI 以保留飞行/俯冲 AI）：
  A 不主动：幻翼在玩家头顶自由飞 14s，玩家不掉血、anger source=NONE。
  B 反击：治疗 → 锚点 tp 把幻翼拉到玩家面前给一拳 → 命中 + source=PLAYER_DIRECT
          → 松手让它自然俯冲，10s 内玩家掉血。

退出码 0=全过。
"""
import json
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

HOST = "mc@192.0.2.10"
CFG = "/home/mc/minecraft/config/peaceandlove.json"
PAL_RPC = ("192.0.2.10", 25585)
SUB = "phsub"

# 开阔平台中心（脚部坐标），flat 测试区
CX, CY, CZ = 70, -57, 30
OBSERVE = 14.0


def log(*a):
    print(*a, flush=True)


def ssh_run(cmd, timeout=30):
    r = subprocess.run(["ssh", HOST, cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def whitelist_has(mob):
    out = ssh_run(
        f"python3 -c \"import json;print('minecraft:{mob}' in json.load(open('{CFG}'))['hostile_whitelist'])\"")
    return out.strip() == "True"


def pal(method, params=None):
    req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
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


def anger_source():
    r = pal("mob.anger", {"name": SUB})
    if not isinstance(r, str):
        return None, r
    m = re.search(r"source=(\w+)", r)
    return (m.group(1) if m else None), r


def hp():
    try:
        return float(rpc("player.state", timeout=5)["health"])
    except Exception:
        return None


def heal():
    for _ in range(4):
        server_rcon("effect give Dev minecraft:instant_health")
        time.sleep(0.25)


def ensure_alive():
    try:
        if rpc("player.state", timeout=5)["dead"]:
            rpc("player.respawn"); time.sleep(2.5)
    except Exception:
        pass
    heal()


def summon_phantom():
    server_rcon(f"kill @e[name={SUB}]")
    time.sleep(0.3)
    # 玩家头顶 6 格，索敌扫描盒 inflate(16,64,16) 必覆盖
    server_rcon(
        f"summon phantom {CX+0.5} {CY+6} {CZ+0.5} "
        f"{{CustomName:'\"{SUB}\"',PersistenceRequired:1b}}")
    time.sleep(1.2)


def main():
    results = []

    def check(label, ok, detail=""):
        log(f"  {'✅' if ok else '❌'} {label} {detail}")
        results.append(ok)

    ensure_alive()
    server_rcon("gamerule doMobSpawning false")
    server_rcon("time set 14000")           # 夜晚，防幻翼阳光燃烧
    server_rcon(f"fill {CX-3} {CY-1} {CZ-3} {CX+3} {CY-1} {CZ+3} stone")  # 地板
    server_rcon(f"tp Dev {CX+0.5} {CY} {CZ+0.5} -90 0")
    time.sleep(0.8)

    # 默认 phantom 在白名单；移出
    if not whitelist_has("phantom"):
        log("  （phantom 本不在白名单）")
    server_rcon("pal whitelist remove phantom")
    time.sleep(0.5)
    log("  remove 后白名单含 phantom:", whitelist_has("phantom"), "（应 False）")

    try:
        # ── A：不主动俯冲 ─────────────────────────────
        log("\n--- A：幻翼自由飞，玩家不打，观察 %.0fs ---" % OBSERVE)
        summon_phantom()
        hp0 = hp()
        t0 = time.time()
        min_hp = hp0
        while time.time() - t0 < OBSERVE:
            time.sleep(1.0)
            h = hp()
            if h is not None:
                min_hp = min(min_hp, h)
        src, raw = anger_source()
        no_dmg = hp0 is not None and min_hp is not None and min_hp >= hp0 - 0.01
        check("A 玩家全程不掉血", no_dmg, f"HP {hp0}→最低 {min_hp}")
        check("A anger source=NONE（索敌被删）", src == "NONE", f"source={src} [{raw}]")
        server_rcon(f"kill @e[name={SUB}]")
        time.sleep(0.5)

        # ── B：打它后俯冲反击 ─────────────────────────
        log("\n--- B：拉来打一拳，放它俯冲反击 ---")
        ensure_alive()
        server_rcon(f"tp Dev {CX+0.5} {CY} {CZ+0.5} -90 0")
        time.sleep(0.5)
        summon_phantom()
        hp0 = hp()

        # 幻翼在高空打不到：反复 tp 到玩家东侧 1.5 格贴脸，attackNearest 直到命中
        hit = False
        detail = ""
        for _ in range(8):
            server_rcon(f"tp @e[name={SUB}] {CX+2.0} {CY+1.0} {CZ+0.5}")
            time.sleep(0.45)
            try:
                r = rpc("player.attackNearest", {"target": "phantom"}, timeout=12)
                detail = str({k: r.get(k) for k in ("distance", "hpBefore", "hpAfter", "hit")}) \
                    if isinstance(r, dict) else str(r)
                if isinstance(r, dict) and r.get("hit"):
                    hit = True
                    break
            except Exception as e:
                detail = "ex:" + str(e)
            time.sleep(0.5)
        time.sleep(0.8)
        src, raw = anger_source()
        check("B 攻击命中", hit, detail)
        check("B source=PLAYER_DIRECT", src == "PLAYER_DIRECT", f"source={src} [{raw}]")

        # 松手，让被 setTarget 的幻翼自然俯冲（不再 tp 锚定）
        dropped = False
        for _ in range(10):
            time.sleep(1.0)
            h = hp()
            if h is not None and hp0 is not None and h < hp0 - 0.01:
                dropped = True
                break
        hp1 = hp()
        check("B 幻翼俯冲反击、玩家掉血", dropped, f"HP {hp0}→{hp1}")
    finally:
        server_rcon(f"kill @e[name={SUB}]")
        server_rcon("pal whitelist add phantom")   # 还原默认白名单
        server_rcon("gamerule doMobSpawning true")
        time.sleep(0.4)
        log("  还原后白名单含 phantom:", whitelist_has("phantom"), "（应 True）")
        ensure_alive()

    log("\n" + "=" * 48)
    ok = all(results)
    log("总判定:", "✅ 幻翼通过" if ok else "❌ 幻翼有失败项")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
