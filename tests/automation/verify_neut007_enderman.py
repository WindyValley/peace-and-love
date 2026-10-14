#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-NEUT-007 真机（末影人）：凝视不激怒；白名单同几何应激怒（对照，排除没对准）；
玩家攻击后正常反击。

源码（Enderman.java）：
  targetSelector: [1] EndermanLookForPlayerGoal extends NearestAttackableTargetGoal
    canUse=getNearestPlayer(isLookingAtMe||isAngryAt)，start 后 ~5tick super.start()
    setTarget(玩家)；[2] HurtByTargetGoal（中立化保留）；[4] ResetUniversalAnger。
  isLookingAtMe：视线向量与「玩家→末影人眼」向量点积 > 1-0.025/dist 且有视线。
  中立化时通用策略删除 [1]（连 [4] 裸 Goal 一起删），[2] 保留。
几何：末影人锚点 E，玩家站正西水平 4 格，yaw=-90、pitch≈-13° 对准其眼睛
  （眼高差 2.55-1.62=0.93）。末影人有 AI（凝视/瞬移 goal 要活着），每 0.5s tp 锚回。
阶段：
  A 默认中立化：持续凝视 8s → target=none、source=NONE、不掉血。
  C 对照：pal whitelist add enderman + 重召，同几何凝视 → target=player（证明视线
     真的构成凝视、A 不是没对准）；随后 remove。
  B 恢复中立化重召：玩家打一拳 → PLAYER_DIRECT/player → 末影人近战反击，玩家掉血。
退出码 0=全过。
"""
import json
import math
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
SUB = "esub2"

EX, EY, EZ = 150.5, -56, 40.5          # 末影人脚部锚点
PX, PZ = EX - 4.0, EZ                   # 玩家：正西水平 4 格
ATTACK_X = EX - 1.5                     # 出拳位：西 1.5 格
EYE_DY = 2.55 - 1.62                    # 末影人眼高 - 玩家眼高
PITCH = -math.degrees(math.atan2(EYE_DY, 4.0))   # ≈ -13.1°
YAW = -90.0                             # 朝东


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


def probe():
    r = pal("mob.anger", {"name": SUB})
    if not isinstance(r, str):
        return None, None, r
    ms = re.search(r"source=(\w+)", r)
    mt = re.search(r"target=([^;]+)", r)
    return (ms.group(1) if ms else None), (mt.group(1).strip() if mt else None), r


def hp():
    try:
        return float(rpc("player.state", timeout=5)["health"])
    except Exception:
        return None


def heal():
    for _ in range(6):
        server_rcon("effect give Dev minecraft:instant_health")
        time.sleep(0.2)


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
    heal()


def summon():
    server_rcon(f"kill @e[name={SUB}]")
    time.sleep(0.3)
    server_rcon(
        f"summon enderman {EX} {EY} {EZ} "
        f"{{CustomName:'\"{SUB}\"',PersistenceRequired:1b}}")
    time.sleep(1.0)


def anchor():
    server_rcon(f"tp @e[name={SUB},limit=1] {EX} {EY} {EZ}")


def stare(seconds, resist):
    """玩家站 PX 持续凝视末影人眼睛；末影人有 AI，每 0.5s tp 锚回。返回 (min_hp, end_src, end_tgt)。"""
    server_rcon(f"tp Dev {PX} {EY} {PZ} {YAW} {PITCH}")
    if resist:
        server_rcon("effect give Dev minecraft:resistance 30 255 true")
    else:
        server_rcon("effect clear Dev minecraft:resistance")
    hp0 = hp()
    min_hp = hp0
    t0 = time.time()
    while time.time() - t0 < seconds:
        rpc("player.look", {"yaw": YAW, "pitch": PITCH}, timeout=4)
        anchor()
        server_rcon(f"tp Dev {PX} {EY} {PZ} {YAW} {PITCH}")
        time.sleep(0.5)
        h = hp()
        if h is not None:
            min_hp = min(min_hp, h)
    s, t, _ = probe()
    return min_hp, hp0, s, t


def main():
    results = []
    def check(label, ok, detail=""):
        log(f"  {'✅' if ok else '❌'} {label} {detail}")
        results.append(ok)

    ensure_alive()
    server_rcon("gamerule doMobSpawning false")
    server_rcon("difficulty normal")
    server_rcon("fill 142 -57 34 158 -57 46 stone")

    # 保证从默认（末影人不在白名单 → 中立化）开始
    server_rcon("pal whitelist remove enderman")
    time.sleep(0.4)

    try:
        # ── A：默认中立化，凝视不激怒 ───────────────
        log("--- A：默认中立化，持续凝视 8s ---")
        summon()
        min_hp, hp0, s, t = stare(8.0, resist=False)
        log(f"  HP {hp0}→最低 {min_hp}；source={s} target={t}")
        check("A 凝视不激怒（target=none、NONE）", t == "none" and s == "NONE",
              f"source={s} target={t}")
        check("A 凝视期不掉血", min_hp is not None and hp0 is not None and min_hp >= hp0 - 0.01)
        server_rcon(f"kill @e[name={SUB}]")

        # ── C：白名单对照，同几何凝视必须激怒 ────────
        log("\n--- C（对照）：加入白名单=原版，同几何凝视 8s，应激怒 ---")
        server_rcon("pal whitelist add enderman")
        time.sleep(0.5)
        log("  白名单含 enderman:", whitelist_has("enderman"), "（应 True）")
        summon()
        min_hp2, hp02, s2, t2 = stare(8.0, resist=True)
        log(f"  HP {hp02}→最低 {min_hp2}；source={s2} target={t2}")
        # 白名单怪不经 mod，anger 探针 source 多为 NONE；激怒以「末影人 target=player」为准
        check("C 对照：白名单末影人被凝视激怒（target=player，证明视线有效）",
              t2 == "player", f"target={t2} source={s2}")
        server_rcon(f"kill @e[name={SUB}]")
        server_rcon("pal whitelist remove enderman")
        time.sleep(0.5)
        log("  还原后白名单含 enderman:", whitelist_has("enderman"), "（应 False）")

        # ── B：恢复中立化，打一拳后反击 ─────────────
        log("\n--- B：恢复中立化，玩家攻击，验末影人反击 ---")
        ensure_alive()
        server_rcon("effect clear Dev minecraft:resistance")   # 清掉 C 阶段残留的免伤
        time.sleep(0.3)
        summon()
        hp0 = hp()
        hit, detail = False, ""
        for _ in range(6):
            anchor()
            server_rcon(f"tp Dev {ATTACK_X} {EY} {EZ} -90 0")
            time.sleep(0.3)
            try:
                r = rpc("player.attack", {"target": "enderman"}, timeout=8)
                detail = str(r)[:120]
            except Exception as e:
                detail = "ex:" + str(e)[:120]
            time.sleep(0.4)
            s0, t0p, _ = probe()
            if s0 == "PLAYER_DIRECT" and t0p == "player":
                hit = True
                break
        check("B 攻击命中（PLAYER_DIRECT/player）", hit, detail)

        # 命中后玩家立刻把视角转开（背对末影人）：末影人有 EndermanFreezeWhenLookedAt
        # goal——目标是玩家且被盯着时 navigation.stop() 冻结，MeleeAttackGoal 无法出手。
        # 转开视线解除冻结（玩家仍留在贴身位），再完全放手让它近战。
        rpc("player.look", {"yaw": 90.0, "pitch": 0.0}, timeout=4)
        server_rcon(f"tp Dev {ATTACK_X} {EY} {EZ} 90 0")
        dropped = False
        tt = time.time()
        while time.time() - tt < 9.0:
            time.sleep(0.5)
            h = hp()
            if h is not None and hp0 is not None and h < hp0 - 0.01:
                dropped = True
                break
        hp1 = hp()
        heal()
        check("B 末影人近战反击、玩家掉血（转开视线解除冻结后）", dropped, f"HP {hp0}→{hp1}")
    finally:
        server_rcon(f"kill @e[name={SUB}]")
        server_rcon("pal whitelist remove enderman")
        server_rcon("effect clear Dev minecraft:resistance")
        server_rcon("gamerule doMobSpawning true")
        ensure_alive()
        heal()

    log("\n" + "=" * 48)
    ok = all(results)
    log("总判定:", "✅ 末影人通过" if ok else "❌ 末影人有失败项")
    log("注：瞬移/搬方块属 goalSelector 非攻击行为，本次未单独触发，代码层保留（凝视激怒 goal 删除不影响）。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
