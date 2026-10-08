#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「怪物互打时同族示警保持原版」：铁傀儡近战打 victim，玩家完全不参与。

双通道判定：
  - execute marker 读旁观怪的实际目标（原版 alertOthers 会直接 setTarget）
  - mod 的 mob.anger 读「生气原因」（非玩家伤害不应写 mod 标记，应全 NONE）

预期：
  僵尸(A 类，原生示警)：near(3 格) 和 far(9 格，>kin_alert_radius 4) 都被原版
      喊到 → 目标=铁傀儡、anger=NONE。证明非玩家攻击范围保持原版 35 格，没被收窄。
  骷髅(B 类，mod 补的示警)：near 也不被喊到 → 无目标；但 victim 自己仍反击铁傀儡。

几何（沿 x 轴，玩家不参与，站远处安全台）：
  石壳  victim+傀儡室(宽2格)  石墙  near室(NoAI旁观)  石墙  far室(NoAI旁观)
  ix-1  ix,ix+1              ix+2  ix+4              ix+9  ix+10
"""
import json
import re
import socket
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon

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


def anger(name):
    r = pal("mob.anger", {"name": name})
    if not isinstance(r, str) or "source=" not in r:
        return None, None
    m = re.search(r"source=(\w+);target=(\w+)", r)
    return (m.group(1), m.group(2)) if m else (None, None)


def target_is_golem(name, tag):
    server_rcon(f"kill @e[type=marker,tag={tag}]")
    server_rcon(
        f"execute as @e[name={name},limit=1] on target "
        f"if entity @s[type=iron_golem] run summon marker ~ ~ ~ {{Tags:[\"{tag}\"]}}")
    chk = server_rcon(f"execute if entity @e[type=marker,tag={tag}]")
    server_rcon(f"kill @e[type=marker,tag={tag}]")
    return "passed" in chk.lower()


def has_target(name, tag):
    server_rcon(f"kill @e[type=marker,tag={tag}]")
    server_rcon(
        f"execute as @e[name={name},limit=1] on target run "
        f"summon marker ~ ~ ~ {{Tags:[\"{tag}\"]}}")
    chk = server_rcon(f"execute if entity @e[type=marker,tag={tag}]")
    server_rcon(f"kill @e[type=marker,tag={tag}]")
    return "passed" in chk.lower()


def hurt_time(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] HurtTime")
    m = re.search(r":\s*(-?\d+)[slf]?\s*$", out.strip())
    return int(m.group(1)) if m else 0


def health(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] Health")
    m = re.search(r":\s*([\d.]+)f?\s*$", out.strip())
    return float(m.group(1)) if m else None


def run_case(mob_type, expect_far_alert):
    server_rcon("gamerule doMobSpawning false")
    for n in ("victim", "near", "far"):
        server_rcon(f"kill @e[name={n}]")
    server_rcon("kill @e[name=golem]")
    server_rcon("kill @e[type=marker]")
    time.sleep(0.5)

    # 玩家位置（player.pos 新协议为结构化 dict）
    ppos = rpc("player.pos")
    px, py, pz = float(ppos["x"]), float(ppos["y"]), float(ppos["z"])
    # 测试台放玩家东侧 12 格，避免误入战斗
    ix, iy, iz = int(round(px)) + 12, int(round(py)), int(round(pz))
    log(f"\n=== {mob_type} === 台心 x={ix} y={iy} z={iz}")

    try:
        # 0) 地板：测试台整段脚下一层
        server_rcon(f"fill {ix-2} {iy-1} {iz-2} {ix+12} {iy-1} {iz+2} stone")
        # 1) victim+傀儡 室：内空 3 格宽、3 层高（傀儡 2.7 高；宽 3 防怪卡角）
        server_rcon(f"fill {ix-1} {iy-1} {iz-1} {ix+3} {iy+3} {iz+1} stone")
        server_rcon(f"fill {ix} {iy} {iz} {ix+2} {iy+2} {iz} air")
        # 2) near 室（中心 ix+5，距 victim 4 格）
        server_rcon(f"fill {ix+4} {iy-1} {iz-1} {ix+6} {iy+1} {iz+1} stone")
        server_rcon(f"fill {ix+5} {iy} {iz} {ix+5} {iy} {iz} air")
        # 3) far 室（中心 ix+11）
        server_rcon(f"fill {ix+10} {iy-1} {iz-1} {ix+12} {iy+1} {iz+1} stone")
        server_rcon(f"fill {ix+11} {iy} {iz} {ix+11} {iy} {iz} air")

        # victim 正常 AI（它自己的 HurtByTargetGoal 要运行）放左格，傀儡中间格。
        # 抗性 V 用 effect 命令给（NBT 内联 ActiveEffects 在 1.21.1 易解析失败）：
        # 伤害≈0 打不死，但被打中时 HurtTime 照样触发，攻击事件稳定可查。
        server_rcon(
            f"summon {mob_type} {ix} {iy} {iz} "
            f"{{CustomName:'{{\"text\":\"victim\"}}',PersistenceRequired:1b}}")
        server_rcon("effect give @e[name=victim,limit=1] resistance 60 4 true")
        server_rcon(
            f"summon iron_golem {ix+1} {iy} {iz} "
            f"{{CustomName:'{{\"text\":\"golem\"}}',PersistenceRequired:1b}}")
        # 旁观同族：NoAI 定点（setTarget 由 alertOthers 外部设置，与自身 AI 无关）
        for n, cx in (("near", ix + 5), ("far", ix + 11)):
            server_rcon(
                f"summon {mob_type} {cx} {iy} {iz} "
                f"{{CustomName:'{{\"text\":\"{n}\"}}',PersistenceRequired:1b,NoAI:1b}}")
        time.sleep(1.0)

        # 4) 轮询 victim 是否被打中：身体变红(HurtTime>0) 或 HP 下降。
        #    抗性 V 下单次掉血小但非零，变红窗口仅 0.5s，两个信号都查。
        hp0 = health("victim")
        hit = False
        misses = 0
        for i in range(120):
            ht = hurt_time("victim")
            h = health("victim")
            if ht > 0 or (h is not None and h < (hp0 or 999) - 0.01):
                hit = True
                log(f"  victim 被打中：HP {hp0} -> {h}，HurtTime={ht}")
                break
            if i % 10 == 0:
                gh = health("golem")
                misses += 1
                log(f"  …{i*0.3:.0f}s 未命中 victimHP={h} golemHP={gh}")
            time.sleep(0.2)
        if not hit:
            log("  ❌ 铁傀儡 36s 内没打到 victim，本对照无效")
            return False
        # 多等 1s 让示警传播到旁观同族
        time.sleep(1.0)

        # 5) 双通道判定
        v_src, v_tgt = anger("victim")
        n_t = has_target("near", f"t_n_{mob_type}")
        n_g = target_is_golem("near", f"g_n_{mob_type}")
        n_src, _ = anger("near")
        f_t = has_target("far", f"t_f_{mob_type}")
        f_g = target_is_golem("far", f"g_f_{mob_type}")
        f_src, _ = anger("far")

        log(f"  victim: anger=({v_src},{v_tgt})（非玩家攻击应 NONE；自己会反击傀儡）")
        log(f"  near : 目标存在={n_t} 目标是傀儡={n_g} anger={n_src}")
        log(f"  far  : 目标存在={f_t} 目标是傀儡={f_g} anger={f_src}")

        # 共同前提：mod 标记全程不参与（anger 都应为 NONE）
        mod_silent = v_src == "NONE" and n_src == "NONE" and f_src == "NONE"

        if mob_type == "zombie":
            # A 类：near/far 都应被原版喊到（far 9 格远在原版 35 格内、超出 mod 的 4 格）
            ok = mod_silent and n_g and f_g
            log("  预期: near/far 都被【原版】喊到（far 9 格 > mod 4 格仍通知 = 范围没收窄）")
        else:
            # B 类：near 也不喊（mod 新增能力仅玩家攻击生效）；victim 自身反击保留
            v_fights_back = has_target("victim", f"t_v_{mob_type}")
            ok = mod_silent and not n_g and not f_t and v_fights_back
            log(f"  预期: near/far 都不被喊；victim 自身反击保留={v_fights_back}")

        log("  结果:", "✅ PASS" if ok else "❌ FAIL")
        return ok
    finally:
        for n in ("victim", "near", "far"):
            server_rcon(f"kill @e[name={n}]")
        server_rcon("kill @e[name=golem]")
        server_rcon("kill @e[type=marker]")
        # 拆测试台（保留 iy-1 地板，防止残留实体踩空）
        server_rcon(f"fill {ix-1} {iy} {iz-1} {ix+12} {iy+3} {iz+1} air")
        server_rcon("gamerule doMobSpawning true")


def main():
    # 玩家站到安全观察位（脚下已有永久平台 40,-57 一带时直接复用）
    server_rcon("effect give Dev resistance 60 1 true")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    r1 = run_case("zombie", True) if only in (None, "zombie") else True
    if only:
        sys.exit(0 if r1 else 1)
    time.sleep(1.0)
    r2 = run_case("skeleton", False)
    log("\n" + "=" * 50)
    log(f"僵尸(A 类原版示警保留): {'✅' if r1 else '❌'}")
    log(f"骷髅(B 类非玩家不示警、自身反击保留): {'✅' if r2 else '❌'}")
    sys.exit(0 if r1 and r2 else 1)


if __name__ == "__main__":
    main()
