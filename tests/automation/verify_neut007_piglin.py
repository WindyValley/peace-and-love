#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-NEUT-007 真机（僵尸猪灵群体报复）：仅球形 4 格单层，不外扩 35 格、不链式。

两条传染链（源码 ZombifiedPiglin.java + 本 mod）：
  - 受击 HurtByTargetGoal.setAlertOthers()：被 HurtByTargetGoalMixin 改道 KinAlerter
    （球形 kin_alert_radius 默认 4、严格同类、只通知无目标者、标 KIN_ALERT、不级联）。
  - customServerAiStep → maybeAlertOthers（4-6s 节流、需视线）→ 私有 alertOthers()：
    按 FOLLOW_RANGE(35) AABB 传染所有无目标同类。本 mod ZombifiedPiglinMixin 在
    中立化且目标为玩家时 cancel（非玩家源保留原版）。
几何（开阔平地、无遮挡→若 Mixin 失效外圈必有视线必被传染，使外圈阴性有效）：
  victim 中心；near×3 距中心 2.5 格（4 格内）；far×3 距中心 9 格（远超 4、在 35 内）。
  全部有 AI，每 0.8s tp 回锚点（不改 target 数据）。玩家抗性免伤。
判据（攻击 victim 后观察 13s，覆盖 2-3 个示警周期）：
  victim: target=player, source=PLAYER_DIRECT
  near×3: target=player, source=KIN_ALERT
  far×3:  target=none,   source=NONE   ← 任一圈层 target=player 即外扩/链式失败
退出码 0=全过。
"""
import json
import re
import socket
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

PAL_RPC = ("192.0.2.10", 25585)
CY = -56
# 中心
CX, CZ = 120.5, 40.5
ATTACK_X = 119.0                     # 玩家出拳位（victim 西 1.5）
# name -> (x,y,z)
MOBS = {
    "vic": (CX, CY, CZ),
    "n1": (123.0, CY, 40.5),         # 东 2.5
    "n2": (CX, CY, 43.0),            # 南 2.5
    "n3": (CX, CY, 38.0),            # 北 2.5
    "f1": (129.5, CY, 40.5),         # 东 9
    "f2": (CX, CY, 49.5),            # 南 9
    "f3": (111.5, CY, 40.5),         # 西 9
}
OBSERVE = 13.0


def log(*a):
    print(*a, flush=True)


def pal(method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
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


def probe(name):
    """返回 (source, target) ；target: player/none/<type>。"""
    r = pal("mob.anger", {"name": name})
    if not isinstance(r, str):
        return None, str(r)
    ms = re.search(r"source=(\w+)", r)
    mt = re.search(r"target=([^;]+)", r)
    return (ms.group(1) if ms else None), (mt.group(1).strip() if mt else None)


def hp():
    try:
        return float(rpc("player.state", timeout=5)["health"])
    except Exception:
        return None


def ensure_alive():
    for _ in range(5):
        try:
            st = rpc("player.state", timeout=5)
        except Exception:
            time.sleep(1)
            continue
        if st.get("dead") or (st.get("health") or 0) <= 0.01:
            try:
                rpc("player.respawn", timeout=10)
            except Exception:
                pass
            time.sleep(3)
            continue
        break


def summon_all():
    server_rcon("kill @e[type=zombified_piglin]")
    time.sleep(0.3)
    for name, (x, y, z) in MOBS.items():
        server_rcon(
            f"summon zombified_piglin {x} {y} {z} "
            f"{{CustomName:'\"{name}\"',PersistenceRequired:1b}}")
        server_rcon(f"effect give @e[name={name},limit=1] minecraft:fire_resistance 120 0 true")
    time.sleep(1.0)


def anchor_all():
    for name, (x, y, z) in MOBS.items():
        server_rcon(f"tp @e[name={name},limit=1] {x} {y} {z}")


def main():
    ensure_alive()
    server_rcon("gamerule doMobSpawning false")
    server_rcon("difficulty normal")
    server_rcon("time set 18000")                 # 夜晚，防亡灵燃烧
    server_rcon("fill 108 -57 36 132 -57 52 stone")
    server_rcon(f"tp Dev {ATTACK_X} {CY} {CZ} -90 0")
    server_rcon("effect give Dev minecraft:resistance 120 255 true")  # 免近战伤
    time.sleep(0.8)

    try:
        summon_all()
        anchor_all()
        time.sleep(1.0)
        base = {n: probe(n) for n in MOBS}
        log("基线（召唤后未攻击）:", {n: base[n] for n in MOBS})
        baseline_clean = all(t == "none" for (_s, t) in base.values())
        log(f"  基线全部 target=none: {baseline_clean}")

        # 打 victim：它须是最近同类（距 1.5，最近 near ≥2.5）
        hit = False
        detail = ""
        for _ in range(6):
            anchor_all()
            server_rcon(f"tp Dev {ATTACK_X} {CY} {CZ} -90 0")
            time.sleep(0.3)
            try:
                r = rpc("player.attack", {"target": "zombified_piglin"}, timeout=8)
                detail = str(r)[:120]
            except Exception as e:
                detail = "ex:" + str(e)[:120]
            time.sleep(0.4)
            s_v, t_v = probe("vic")
            if s_v == "PLAYER_DIRECT" and t_v == "player":
                hit = True
                break
        log(f"  攻击 victim 命中={hit} {detail}")

        # 观察 13s，持续锚定，覆盖 2-3 个 4-6s 示警周期
        t0 = time.time()
        while time.time() - t0 < OBSERVE:
            anchor_all()
            time.sleep(0.8)
        final = {n: probe(n) for n in MOBS}
        log("最终状态:")
        for n in MOBS:
            log(f"   {n:3s} source={final[n][0]} target={final[n][1]}")

        results = []
        def check(label, ok, detail2=""):
            log(f"  {'✅' if ok else '❌'} {label} {detail2}")
            results.append(ok)

        check("基线无提前激怒", baseline_clean)
        check("命中 victim（PLAYER_DIRECT/player）", hit)
        sv, tv = final["vic"]
        check("victim 目标=玩家、PLAYER_DIRECT", sv == "PLAYER_DIRECT" and tv == "player")
        near_ok = all(final[n] == ("KIN_ALERT", "player") for n in ("n1", "n2", "n3"))
        near_detail = {n: final[n] for n in ("n1", "n2", "n3")}
        check("4 格内 3 只被单层示警（KIN_ALERT/player）", near_ok, str(near_detail))
        far_ok = all(t == "none" for (_s, t) in (final[n] for n in ("f1", "f2", "f3")))
        far_detail = {n: final[n] for n in ("f1", "f2", "f3")}
        check("9 格外 3 只不被传染（target=none，无 35 格外扩/链式）", far_ok, str(far_detail))
    finally:
        server_rcon("kill @e[type=zombified_piglin]")
        server_rcon("effect clear Dev minecraft:resistance")
        server_rcon("time set day")
        server_rcon("gamerule doMobSpawning true")
        ensure_alive()
        server_rcon("effect give Dev minecraft:instant_health")

    log("\n" + "=" * 48)
    ok = all(results)
    log("总判定:", "✅ 僵尸猪灵通过" if ok else "❌ 僵尸猪灵有失败项")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
