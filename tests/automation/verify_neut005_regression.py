#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-NEUT-005 回归：谓词收窄后，其余默认白名单生物移出白名单时
仍正确中立化（不主动攻击），打它仍反击。本次唯一广面改动是 GoalBasedStrategy
移除谓词，故回归确认没误伤这些生物的目标选择/反击链。

生物：shulker / vindicator(Johnny:1b) / vindicator(普通) / pillager / evoker / vex。
两阶段（手法同已通过的地狱三怪）：
  A 玩家有抗性、怪每 0.8s 拉回东侧锚点，观察 6s：source=NONE、target=none、不掉血。
  B 清抗性，attack 命中（PLAYER_DIRECT/player），拉锚点给 7s 反击窗口：target=player。
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
CX, CY, CZ = 200.5, -56, 40.5
AX, AY, AZ = 202.5, -56, 40.5        # 怪锚点（东 2 格）

# (key, mob_id_for_rpc, summon_type, extra_nbt)
MOBS = [
    ("shulker", "shulker", "minecraft:shulker", ""),
    ("johnny", "vindicator", "minecraft:vindicator", "Johnny:1b,"),
    ("vindicator", "vindicator", "minecraft:vindicator", ""),
    ("pillager", "pillager", "minecraft:pillager", ""),
    ("evoker", "evoker", "minecraft:evoker", ""),
    ("vex", "vex", "minecraft:vex", ""),
]
WHITELIST_IDS = ["shulker", "vindicator", "pillager", "evoker", "vex"]


def log(*a):
    print(*a, flush=True)


def ssh_run(cmd, timeout=30):
    r = subprocess.run(["ssh", HOST, cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def wl_has(mob):
    out = ssh_run(
        f"python3 -c \"import json;print('minecraft:{mob}' in json.load(open('{CFG}'))['hostile_whitelist'])\"")
    return out.strip() == "True"


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
    r = pal("mob.anger", {"name": name})
    if not isinstance(r, str):
        return None, None
    ms = re.search(r"source=(\w+)", r)
    mt = re.search(r"target=([^;]+)", r)
    return (ms.group(1) if ms else None), (mt.group(1).strip() if mt else None)


def hp():
    try:
        return float(rpc("player.state", timeout=5)["health"])
    except Exception:
        return None


def heal():
    for _ in range(6):
        server_rcon("effect give Dev minecraft:instant_health")
        time.sleep(0.15)


def ensure_alive():
    for _ in range(5):
        try:
            st = rpc("player.state", timeout=5)
        except Exception:
            time.sleep(1); continue
        if st.get("dead") or (st.get("health") or 0) <= 0.01:
            try:
                rpc("player.respawn", timeout=10)
            except Exception:
                pass
            time.sleep(3); continue
        break


def main():
    ensure_alive()
    server_rcon("gamerule doMobSpawning false")
    server_rcon("difficulty normal")
    server_rcon("fill 196 -57 36 208 -57 44 stone")
    # 验前全部移出白名单（只影响之后新召唤）
    for mid in WHITELIST_IDS:
        server_rcon(f"pal whitelist remove {mid}")
    time.sleep(0.6)

    results = {}
    try:
        for key, rpc_id, stype, extra in MOBS:
            log(f"\n===== {key} =====")
            ensure_alive()
            if (hp() or 0) < 19:      # 尸体/残血不许开测，避免 0→0 假通过
                heal()
            server_rcon(f"kill @e[name={key}]")
            server_rcon(
                f"summon {stype} {AX} {AY} {AZ} "
                f"{{CustomName:'\"{key}\"',PersistenceRequired:1b,{extra}}}")
            time.sleep(1.0)

            # ── A：不主动（玩家有抗性）──
            server_rcon("effect clear Dev minecraft:resistance")
            server_rcon("effect give Dev minecraft:resistance 20 255 true")
            server_rcon(f"tp Dev {CX} {CY} {CZ} -90 0")
            hp0 = hp()
            t0 = time.time()
            while time.time() - t0 < 6.0:
                server_rcon(f"tp @e[name={key},limit=1] {AX} {AY} {AZ}")
                time.sleep(0.8)
            sa, ta = probe(key)
            hpa = hp()
            alive_a = hp0 is not None and hpa is not None and hpa > 18
            a_ok = sa == "NONE" and ta == "none" and alive_a
            log(f"  [A] source={sa} target={ta} HP {hp0}→{hpa} {'✅' if a_ok else '❌'}")

            # ── B：打后反击（抗性保命，主判据=PLAYER_DIRECT 且 target=player）──
            ensure_alive()
            server_rcon("effect give Dev minecraft:resistance 20 10 true")  # 高减伤保命
            time.sleep(0.3)
            hp0 = hp()
            hit = False
            for _ in range(6):
                server_rcon(f"tp @e[name={key},limit=1] {AX} {AY} {AZ}")
                server_rcon(f"tp Dev {CX} {CY} {CZ} -90 0")
                time.sleep(0.3)
                try:
                    rpc("player.attack", {"target": rpc_id}, timeout=8)
                except Exception:
                    pass
                time.sleep(0.4)
                sb, tb = probe(key)
                if sb == "PLAYER_DIRECT" and tb == "player":
                    hit = True
                    break
            tgt_player = False
            dropped = False
            t0 = time.time()
            while time.time() - t0 < 6.0:
                server_rcon(f"tp @e[name={key},limit=1] {AX} {AY} {AZ}")
                server_rcon(f"tp Dev {CX} {CY} {CZ} -90 0")
                time.sleep(0.7)
                _s, tb = probe(key)
                if tb == "player":
                    tgt_player = True
                h = hp()
                if h is not None and hp0 is not None and h < hp0 - 0.01:
                    dropped = True
            hpb = hp()
            heal()
            b_ok = hit and tgt_player
            log(f"  [B] 命中PLAYER_DIRECT={hit} 反击target=player={tgt_player} 掉血旁证={dropped} "
                f"HP {hp0}→{hpb} {'✅' if b_ok else '❌'}")
            results[key] = a_ok and b_ok
            server_rcon(f"kill @e[name={key}]")
            server_rcon("effect clear Dev minecraft:resistance")
    finally:
        for mid in WHITELIST_IDS:
            server_rcon(f"pal whitelist add {mid}")
        server_rcon("kill @e[type=shulker]")
        server_rcon("kill @e[type=vex]")
        server_rcon("effect clear Dev minecraft:resistance")
        server_rcon("gamerule doMobSpawning true")
        ensure_alive(); heal()
        time.sleep(0.4)
        log("\n白名单还原：" + ", ".join(f"{m}={wl_has(m)}" for m in WHITELIST_IDS))

    log("\n" + "=" * 48)
    for k, ok in results.items():
        log(f"  {k}: {'✅' if ok else '❌'}")
    allok = all(results.values())
    log("总判定:", "✅ 回归全部通过" if allok else "❌ 有回归失败")
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
