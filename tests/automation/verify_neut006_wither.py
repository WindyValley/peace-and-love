#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-NEUT-006 真机（凋灵）：真实图案召唤 + 出生爆炸 + 主头反击 + 两侧头中立化。

召唤走最真实机制：玩家亲手放最后一个凋灵骷髅头，触发 WitherSkullBlock 的
setPlacedBy → checkSpawn（makeInvulnerable Invul=220）。需要 mc-client-rpc 的
player.placeBlock 原语（真实 gameMode.useItemOn）。

pattern（源码 aisle("^^^","###","~#~")，y0 底→y2 头）：
  y0 仅中央 1 灵魂沙（两侧必须空气）；y1 三灵魂沙横排；y2 三 floor 骷髅头。
出生爆炸：customServerAiStep 无敌倒计时到 0 → explode(eyeY,7,MOB)。
攻击头：主头 RangedAttackGoal(head=0)+HurtByTargetGoal(保留)，
  NearestAttackableTargetGoal(被删)；侧头在 customServerAiStep 硬编码索敌+idle乱射。
  三条开火路径汇到私有 performRangedAttack(int head,..)，Mixin 拦 head>=1、放行 head=0。

阶段：0 真实放置图案召唤 + 骑头鸡验爆炸；A 无目标 24s 不掉血/NONE；B 打一拳主头反击。
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
SUB = "wsub"
ESUB = "esub"

BY = -56
WX, WZ = 93, 60
PLACE_X, PLACE_Z = WX + 0.5, WZ + 2.5     # 亲手放头站位（中央头正南 2.5 格）
FAR_X, FAR_Z = 75.5, WZ + 0.5             # 爆炸躲避点（地板范围内，水平 18 格）
PX, PY, PZ = 86.5, BY, WZ + 0.5           # A 观察点（西侧约 7 格）
CLOSE_X = 91.5                            # B 贴身点（西侧 1.5）
OBSERVE_A = 24.0


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
        h = st.get("health") or 0
        if st.get("dead") or h <= 0.01:
            try:
                rpc("player.respawn", timeout=10)
            except Exception:
                pass
            time.sleep(3)
            continue
        break
    heal()


def exists(sel):
    return "Test passed" in server_rcon(f"execute if entity {sel}")


def block_at(x, y, z, block):
    return "Test passed" in server_rcon(f"execute if block {x} {y} {z} {block}")


def kill_all():
    server_rcon("kill @e[type=wither]")
    server_rcon(f"kill @e[name={ESUB}]")


def anchor():
    server_rcon(f"tp @e[name={SUB}] {WX+0.5} {BY} {WZ+0.5}")


def main():
    results = []

    def check(label, ok, detail=""):
        log(f"  {'✅' if ok else '❌'} {label} {detail}")
        results.append(ok)

    ensure_alive()
    server_rcon("gamerule doMobSpawning false")
    server_rcon("difficulty normal")
    server_rcon("gamemode survival Dev")
    server_rcon("fill 74 -57 54 102 -57 66 stone")
    kill_all()

    try:
        # ── 0：真实图案召唤 ─────────────────────────
        log("--- 0：搭 T 形底座，玩家亲手放 3 个骷髅头 ---")
        for dx in (-1, 0, 1):
            for yy in (BY, BY + 1, BY + 2):
                server_rcon(f"setblock {WX+dx} {yy} {WZ} air")
        time.sleep(0.3)
        server_rcon(f"setblock {WX} {BY} {WZ} soul_sand")            # y0 仅中央
        for dx in (-1, 0, 1):
            server_rcon(f"setblock {WX+dx} {BY+1} {WZ} soul_sand")   # y1 三横排
        base_ok = (all(block_at(WX + dx, BY + 1, WZ, "soul_sand") for dx in (-1, 0, 1))
                   and block_at(WX, BY, WZ, "soul_sand")
                   and block_at(WX - 1, BY, WZ, "air")
                   and block_at(WX + 1, BY, WZ, "air"))
        log(f"  底座就绪（y0 单脚+y1 三横+y0 两侧空气）={base_ok}")

        server_rcon(f"tp Dev {PLACE_X} {BY} {PLACE_Z} 180 0")
        time.sleep(0.5)
        server_rcon("item replace entity Dev weapon.mainhand with minecraft:wither_skeleton_skull 3")
        time.sleep(0.3)
        r1 = rpc("player.placeBlock", {"x": WX - 1, "y": BY + 1, "z": WZ, "face": "up"}, timeout=8)
        r3 = rpc("player.placeBlock", {"x": WX + 1, "y": BY + 1, "z": WZ, "face": "up"}, timeout=8)
        time.sleep(0.3)
        r2 = rpc("player.placeBlock", {"x": WX, "y": BY + 1, "z": WZ, "face": "up"}, timeout=8)
        log(f"  放置 侧左={r1.get('clientResult')} 中央={r2.get('clientResult')} 侧右={r3.get('clientResult')} 主手余={r2.get('mainhand')}")
        time.sleep(0.6)

        spawned = exists("@e[type=wither]")
        check("玩家真实放置图案召唤出凋灵", spawned)

        if spawned:
            # 玩家第一时间撤到爆炸半径外（爆炸在约 11s 后）
            server_rcon(f"tp Dev {FAR_X} {BY} {FAR_Z} 180 0")
            server_rcon(
                f"data merge entity @e[type=wither,limit=1,sort=nearest] "
                f"{{CustomName:'\"{SUB}\"',PersistenceRequired:1b}}")
            server_rcon(
                f"summon chicken {WX+0.5} {BY+3} {WZ+0.5} "
                f"{{CustomName:'\"{ESUB}\"',NoAI:1b,PersistenceRequired:1b}}")
            time.sleep(0.4)
            server_rcon(f"ride @e[name={ESUB},limit=1] mount @e[name={SUB},limit=1]")
            time.sleep(0.4)
            chick_before = exists(f"@e[name={ESUB},type=chicken]")
            log(f"  骑头鸡就位={chick_before}，玩家已撤，等无敌期+爆炸 ~14s ...")
            time.sleep(14.0)
            chick_after = exists(f"@e[name={ESUB},type=chicken]")
            check("出生爆炸保留（骑头定点鸡被炸死）",
                  chick_before and not chick_after, f"鸡 {chick_before}→{chick_after}")
        else:
            check("出生爆炸保留（骑头定点鸡被炸死）", False, "凋灵未生成，跳过")
        server_rcon(f"kill @e[name={ESUB}]")
        server_rcon("item replace entity Dev weapon.mainhand with air")

        # ── A：无目标，侧头锁定 + idle 乱射全被拦 ──
        log("\n--- A：玩家进侧头索敌盒，不打，观察 %.0fs ---" % OBSERVE_A)
        ensure_alive()
        anchor()
        server_rcon(f"tp Dev {PX} {PY} {PZ} -90 0")
        time.sleep(0.8)
        hp0 = hp()
        t0, min_hp = time.time(), hp0
        while time.time() - t0 < OBSERVE_A:
            anchor()
            time.sleep(0.8)
            h = hp()
            if h is not None:
                min_hp = min(min_hp, h)
        src, raw = anger_source()
        no_dmg = hp0 is not None and min_hp is not None and min_hp >= hp0 - 0.01
        check("A 观察期不掉血（侧头锁定+idle乱射被拦、主头无目标）",
              no_dmg, f"HP {hp0}→最低 {min_hp}")
        check("A anger=NONE", src == "NONE", f"source={src} [{raw}]")

        # ── B：主头反击 ─────────────────────────────
        log("\n--- B：贴身打一拳，验主头 head0 反击 ---")
        ensure_alive()
        if (hp() or 0) < 19:
            heal()
        hp0 = hp()
        hit, direct, detail = False, False, ""
        for _ in range(6):
            anchor()
            server_rcon(f"tp Dev {CLOSE_X} {PY} {PZ} -90 0")
            time.sleep(0.35)
            try:
                r = rpc("player.attack", {"target": "wither"}, timeout=8)
                detail = str(r)[:120]
            except Exception as e:
                detail = "ex:" + str(e)[:120]
            time.sleep(0.35)
            src0, _ = anger_source()
            if src0 == "PLAYER_DIRECT":
                hit, direct = True, True
                break
        check("B 攻击命中（服务端 PLAYER_DIRECT 硬证据）", hit, detail)
        check("B source=PLAYER_DIRECT（HurtByTargetGoal 保留）", direct, "")

        dropped = False
        t0 = time.time()
        while time.time() - t0 < 8.0:
            anchor()
            server_rcon(f"tp Dev {PX} {PY} {PZ} -90 0")
            time.sleep(0.4)
            h = hp()
            if h is not None and hp0 is not None and h < hp0 - 0.01:
                dropped = True
                break
        hp1 = hp()
        heal()
        check("B 主头 head0 开火反击、玩家掉血", dropped, f"HP {hp0}→{hp1}")
    finally:
        kill_all()
        for dx in (-1, 0, 1):
            for yy in (BY, BY + 1, BY + 2):
                server_rcon(f"setblock {WX+dx} {yy} {WZ} air")
        server_rcon("item replace entity Dev weapon.mainhand with air")
        server_rcon("gamerule doMobSpawning true")
        ensure_alive()
        heal()

    log("\n" + "=" * 48)
    ok = all(results)
    log("总判定:", "✅ 凋灵通过" if ok else "❌ 凋灵有失败项")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
