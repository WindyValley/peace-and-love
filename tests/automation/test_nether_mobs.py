#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""地狱三怪真机双向验证：piglin / piglin_brute / hoglin。

场地：地狱平台中心 (100,70,100)，玩家站中心朝东(yaw=-90)，
怪锚点在东侧 2 格 (102.5,70,100.5)。

每只怪两阶段：
  A（不主动打）：6s 内每 0.8s 把怪 tp 回锚点，每秒读玩家HP + mob.anger。
    期望 HP 恒定、source=NONE（无因攻击被拦）。
  B（先动手）：治疗满血 → player.attack 打一拳 → 期望 source=PLAYER_DIRECT
    且玩家 HP 下降（反击放行）。

通过标准：两阶段全过。退出码 0=全过，非0=有失败。
"""
import json
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon

DIM = "minecraft:the_nether"
PX_, PY_, PZ_ = 100.5, 70, 100.5          # 玩家
AX, AY, AZ_ = 102.5, 70, 100.5             # 怪锚点（东 2 格）
PAL_RPC = ("192.0.2.10", 25585)
SUB = "sub"

MOBS = [
    ("piglin", "minecraft:piglin"),
    ("piglin_brute", "minecraft:piglin_brute"),
    ("hoglin", "minecraft:hoglin"),
]


# ── PAL 愤怒探针 ──────────────────────────────────────────────

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
        return None
    m = re.search(r"source=(\w+)", r)
    return m.group(1) if m else None


# ── 玩家/怪 ─────────────────────────────────────────────────

def player_hp():
    """从结构化 player.state 读血量；连接/协议异常返回 None。"""
    try:
        return float(rpc("player.state", timeout=5)["health"])
    except Exception:
        return None


def in_nether(cmd):
    return server_rcon(f"execute in {DIM} run {cmd}")


def summon(mob_type):
    in_nether("kill @e[name=sub]")
    time.sleep(0.3)
    in_nether(f"summon {mob_type} {AX} {AY} {AZ_} "
              f"{{CustomName:'\"{SUB}\"',PersistenceRequired:1b}}")
    time.sleep(1.0)


def pull_anchor():
    in_nether(f"tp @e[name=sub] {AX} {AY} {AZ_}")


def cleanup():
    in_nether("kill @e[name=sub]")


# ── 两阶段 ─────────────────────────────────────────────────

def phase_a():
    hp0 = player_hp()
    t0 = time.time()
    while time.time() - t0 < 6.0:
        pull_anchor()
        time.sleep(0.8)
    # 读判据（持续约 6s 后）
    src = anger_source()
    hp1 = player_hp()
    no_damage = (hp0 is not None and hp1 is not None and hp1 >= hp0 - 0.01)
    ok = no_damage and src == "NONE"
    print(f"   [A] HP {hp0}→{hp1} source={src}  "
          f"{'✓ 无伤、无因' if ok else '✗'}")
    return ok


def phase_b(mob_key):
    # 满血重来，先清一下愤怒判定基线
    server_rcon("effect give Dev minecraft:instant_health")
    time.sleep(0.6)
    server_rcon("effect give Dev minecraft:instant_health")
    time.sleep(0.6)
    hp0 = player_hp()
    # 打：怪（尤其猪灵）会漂移导致超距，拉回锚点后重试，直到真正命中
    hit = False
    for _ in range(5):
        pull_anchor()
        time.sleep(0.5)
        try:
            atk = rpc("player.attack", {"target": mob_key}, timeout=8)
            print("   攻击:", {k: atk[k] for k in ("target", "distance", "hpBefore", "hpAfter", "hit")})
        except Exception as e:
            print("   攻击失败（重试）:", str(e))
            time.sleep(0.6)
            continue
        time.sleep(1.0)
        src = anger_source()
        if atk.get("hit") and src == "PLAYER_DIRECT":
            hit = True
            break
        time.sleep(0.6)
    # 给怪 6s 反击窗口
    dropped = False
    for _ in range(6):
        time.sleep(1)
        h = player_hp()
        if h is not None and hp0 is not None and h < hp0 - 0.01:
            dropped = True
    hp1 = player_hp()
    src = anger_source()
    ok = dropped and src == "PLAYER_DIRECT"
    print(f"   [B] HP {hp0}→{hp1} source={src} 命中={hit} "
          f"{'✓ 被打反击' if ok else '✗ (攻击未命中/门控未放行)'}")
    return ok


def ensure_alive():
    """玩家若死亡则复活（落在出生点，之后 tp 回平台），并治疗回满。"""
    try:
        dead = bool(rpc("player.state", timeout=5)["dead"])
    except Exception:
        dead = False
    if dead:
        rpc("player.respawn"); time.sleep(2.5)
    server_rcon("effect give Dev minecraft:instant_health")
    time.sleep(0.5)


def main():
    # 开场：玩家若死亡先复活
    ensure_alive()
    # 确保玩家在地狱平台中心朝东
    in_nether(f"tp Dev {PX_} {PY_} {PZ_} -90 0")
    time.sleep(1.0)
    # 关刷怪防干扰
    server_rcon("gamerule doMobSpawning false")

    results = {}
    try:
        for key, type_id in MOBS:
            print(f"\n===== {key} =====")
            ensure_alive()                       # 每只怪前保证活着满血
            in_nether(f"tp Dev {PX_} {PY_} {PZ_} -90 0")
            time.sleep(0.8)
            summon(type_id)
            a = phase_a()
            b = phase_b(key)
            results[key] = a and b
            cleanup()
    finally:
        cleanup()
        server_rcon("gamerule doMobSpawning true")
        ensure_alive()
        in_nether(f"tp Dev {PX_} {PY_} {PZ_}")

    print("\n========== 总结 ==========")
    for key, ok in results.items():
        print(f"  {key}: {'✓ 双向通过' if ok else '✗ 失败'}")
    all_ok = all(results.values())
    print("\n总判定:", "✅ 地狱三怪全部通过" if all_ok else "❌ 有失败项")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
