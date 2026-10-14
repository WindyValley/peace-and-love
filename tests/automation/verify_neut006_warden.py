#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-NEUT-006 监守者回归：自然召唤（尖啸体 + STEP），确认本轮零改动下
BrainAttackGate 仍拦 Sonic Boom/近战（不打不掉血），玩家打后仍反击。

要点（见 skill brain-based-mobs，0.0.2 已全绿）：
  - 不能 /summon（5s 钻地自灭）；尖啸体 can_summon 是 blockstate；只认玩家 STEP 振动，
    跳跃/红石/setblock 无效；warning 1→4 约 38s 走动，循环 ≥55s。
  - 计数在玩家（WardenSpawnTracker），blockdata warning_level 只是镜像。
  - 钻出期（is_emerging，约 6-8s）打它只掉血不激怒，等记忆消失再打。
  - 绝不 tp 监守者，只 tp 玩家；命中读服务端，反击=玩家掉血/死亡。

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
SUB = "warden"
# 直道沿 x 轴，中央尖啸体
CX, FY, CZ = 236, -56, 60
SHX, SHY, SHZ = CX, FY, CZ           # 尖啸体方块（地板 y=-57 之上）
X_LO, X_HI = CX - 5, CX + 5


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


def anger():
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


def dead():
    try:
        return bool(rpc("player.state", timeout=5).get("dead"))
    except Exception:
        return False


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
    for _ in range(5):
        server_rcon("effect give Dev minecraft:instant_health")
        time.sleep(0.15)


def warden_exists():
    return "Test passed" in server_rcon("execute if entity @e[type=warden]")


def warning_level():
    # 读完整 block NBT，子路径读法格式不稳定；NBT 形如 {warning_level: 2, ...}
    out = server_rcon(f"data get block {SHX} {SHY} {SHZ}")
    m = re.search(r"warning_level:\s*(-?\d+)", out)
    return int(m.group(1)) if m else -1


def emerging():
    out = server_rcon("data get entity @e[type=warden,limit=1] Brain")
    return "is_emerging" in out


def warden_hp():
    out = server_rcon("data get entity @e[type=warden,limit=1] Health")
    m = re.search(r"([\d.]+)f?$", out.strip())
    try:
        return float(out.split()[-1].rstrip("f"))
    except Exception:
        return None


def main():
    results = []
    def check(label, ok, detail=""):
        log(f"  {'✅' if ok else '❌'} {label} {detail}")
        results.append(ok)

    ensure_alive()
    server_rcon("gamerule doMobSpawning false")
    server_rcon("difficulty normal")
    # 三层厚平台（-59..-57 stone），逼监守者在最近表面 -56 钻出、不掉到板下；范围够大
    server_rcon(f"fill {CX-10} -59 {CZ-8} {CX+10} -57 {CZ+8} stone")
    server_rcon(f"fill {CX-10} -56 {CZ-8} {CX+10} -53 {CZ+8} air")
    server_rcon("kill @e[type=warden]")
    # 玩家先到直道（站立层 FY），保证区块加载
    server_rcon(f"tp Dev {CX-3.5} {FY} {CZ+0.5} -90 0")
    time.sleep(0.6)
    server_rcon(f"setblock {SHX} {SHY} {SHZ} air")
    time.sleep(0.2)
    # 尖啸体（blockstate can_summon=true），站在 -57 板上
    server_rcon(f"setblock {SHX} {SHY} {SHZ} minecraft:sculk_shrieker[can_summon=true]")
    time.sleep(0.3)
    can = "Test passed" in server_rcon(
        f"execute if block {SHX} {SHY} {SHZ} minecraft:sculk_shrieker[can_summon=true]")
    log("尖啸体 can_summon=true:", can)

    try:
        # ── 走动 STEP 攒警告，自然召唤 ──────────────
        log("--- 玩家绕尖啸体持续步行（STEP），攒 warning 1→4，最多 170s ---")
        # 手法（Fabric 实证，踩坑两次）：
        #  ① 绝不能周期性 tp——tp 是服务端瞬移、不产生 STEP 游戏事件，会把连续
        #     步行的振动打断，尖啸体只收到最初两三次后 warning 永久卡死（实测 165s 停 2）。
        #  ② 绝不能 player.look 瞬时转 180° 掉头——急转触发客户端/服务端移动去同步，
        #     玩家会被橡皮筋拉回并永久停止（实测转身后走 7 格即钉死）。
        #  正确做法：W 键一直按（一次 player.move），yaw 每 0.2s 平滑 +24°（约 2s 一圈），
        #  玩家绕半径约 3 格的圆持续走、全程在尖啸体 8 格振动监听盒内，每步都是真实 STEP。
        #  向东起步、yaw 递增（右转向南）时圆心在起点南侧，故从尖啸体【北侧】起步让圆心落尖啸体。
        #  玩家侧每次警告有 200t(10s) 冷却，全新世界 0→4 约 40s；tracker 有残留则更快。
        server_rcon(f"tp Dev {SHX+0.5} {FY} {SHZ-3.5} -90 0")
        time.sleep(0.5)
        rpc("player.move", {"forward": 1.0, "strafe": 0.0}, timeout=4)
        yaw = -90.0
        last_turn = time.time()
        t0 = time.time()
        max_warn = -1
        last_log = 0.0
        spawned = False
        while time.time() - t0 < 170:
            now = time.time()
            if now - last_turn > 0.2:
                yaw += 24.0                       # 平滑右转，W 不放
                rpc("player.look", {"yaw": yaw, "pitch": 0.0}, timeout=3)
                last_turn = now
            time.sleep(0.1)
            w = warning_level()
            max_warn = max(max_warn, w)
            if now - last_log > 5:
                log(f"    t={now-t0:4.0f}s warning_level={w}")
                last_log = now
            if warden_exists():
                spawned = True
                log(f"  监守者已自然召唤（最高 warning={max_warn}），停止走动")
                break
        rpc("player.stop", timeout=4)
        check("尖啸体能召唤（can_summon blockstate）", can)
        check("自然召唤出监守者（无 5s 自灭）", spawned, f"最高 warning={max_warn}")
        if not spawned:
            raise SystemExit(1)

        # 等钻出结束（is_emerging 消失），最多 12s
        t0 = time.time()
        while time.time() - t0 < 12:
            if not emerging():
                break
            time.sleep(0.8)
        log("  钻出结束，is_emerging 已消失")
        # 自然召唤的监守者无 CustomName，探针按 name 找不到；钻出结束后命名（不 tp 怪）
        named = False
        for attempt in range(6):
            mr = server_rcon("data merge entity @e[type=warden,limit=1] {CustomName:'\"warden\"'}")
            time.sleep(0.4)
            chk = server_rcon("execute if entity @e[name=warden,type=warden]")
            if "Test passed" in chk:
                named = True
                break
            if attempt == 0:
                log("  merge 返回:", mr.strip(), "| 读回:",
                    server_rcon("data get entity @e[type=warden,limit=1] CustomName").strip())
            time.sleep(0.6)
        log("  命名后 @e[name=warden,type=warden] 存在:", named)

        # ── A：不打，靠近，确认不主动攻击 ──────────
        ensure_alive()
        server_rcon("effect clear Dev minecraft:resistance")
        # 停在监守者南侧约 3 格（产生振动但不动手）
        wy = server_rcon("data get entity @e[type=warden,limit=1] Pos").strip()
        m = re.search(r"\[(-?[\d.]+)d, *(-?[\d.]+)d, *(-?[\d.]+)d\]", wy)
        wxx, wyy, wzz = (float(g) for g in m.groups()) if m else (CX, FY, CZ)
        log(f"  监守者位置 ≈ ({wxx:.1f},{wyy:.1f},{wzz:.1f})")
        server_rcon(f"tp Dev {wxx:.2f} {wyy:.1f} {wzz+3.0:.2f} 0 0")
        hp0 = hp()
        t0 = time.time()
        min_hp = hp0
        while time.time() - t0 < 12.0:
            time.sleep(1.0)
            h = hp()
            if h is not None:
                min_hp = min(min_hp, h)
        sa, ta, raw = anger()
        log(f"  [A] HP {hp0}→最低 {min_hp} source={sa} target={ta}")
        check("A 不主动攻击（不掉血、PLAYER 愤怒门控未解锁）",
              min_hp is not None and hp0 is not None and min_hp >= hp0 - 0.01,
              f"source={sa} target={ta}")

        # ── B：打一拳，验反击 ──────────────────────
        ensure_alive()
        server_rcon("effect clear Dev minecraft:resistance")
        time.sleep(0.3)
        hp_before_attack = hp()
        whp0 = warden_hp()
        # 贴到监守者 z+1.4，0.4s 内出拳
        hit = False
        for _ in range(6):
            server_rcon(f"tp Dev {wxx:.2f} {wyy:.1f} {wzz+1.6:.2f} 180 0")
            time.sleep(0.35)
            try:
                rr = rpc("player.attack", {"target": "warden"}, timeout=8)
                if not hit:
                    log("    attack 返回:", str(rr)[:140])
            except Exception as e:
                log("    attack 异常:", str(e)[:140])
            time.sleep(0.6)
            whp1 = warden_hp()
            sb, tb, _ = anger()
            if whp0 is not None and whp1 is not None and whp1 < whp0 - 0.01:
                hit = True
            if sb == "PLAYER_DIRECT":
                hit = True
                break
        sb, tb, _ = anger()
        check("B 命中监守者（服务端掉血 / PLAYER_DIRECT）", hit,
              f"HP {whp0}→{warden_hp()} source={sb}")

        # 反击窗口：近战/Sonic Boom，玩家掉血或死亡即算（warden 伤害高，可能秒杀）
        retaliated = False
        t0 = time.time()
        while time.time() - t0 < 10.0:
            time.sleep(0.6)
            if dead():
                retaliated = True
                break
            h = hp()
            if h is not None and hp_before_attack is not None and h < hp_before_attack - 0.01:
                retaliated = True
                break
        check("B 监守者反击（玩家掉血/死亡）", retaliated,
              f"HP {hp_before_attack}→{hp()}")
    finally:
        rpc("player.stop", timeout=4)
        server_rcon("kill @e[type=warden]")
        server_rcon(f"setblock {SHX} {SHY} {SHZ} air")
        server_rcon("effect clear Dev minecraft:resistance")
        server_rcon("gamerule doMobSpawning true")
        ensure_alive()

    log("\n" + "=" * 48)
    ok = all(results)
    log("总判定:", "✅ 监守者回归通过" if ok else "❌ 监守者回归失败")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
