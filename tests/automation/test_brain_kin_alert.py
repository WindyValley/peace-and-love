#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brain 系同族示警真机验证（两轮：猪灵 NeutralMob / 疣猪兽 非 NeutralMob）。

每轮几何（地狱平台，y=70；玩家 100.5,70,100.5 朝东）：
  vic 受害者      (102.5,70,100.5)  距玩家 2
  n1  同族近      (102.5,70,98.5)   距 vic 2
  n2  同族近      (102.5,70,102.5)  距 vic 2
  nk  异族对照    (104.5,70,100.5)  距 vic 2（不示警）
  仅猪灵轮加：
  s1  二圈同族   (102.5,70,94.5)   距 vic 6、距 n1 4（验单层不级联）

判定：
  攻击 vic 后：vic=PLAYER_DIRECT/target=player；n1,n2=KIN_ALERT/player；
    nk=NONE；s1（若有）=NONE。
  脱战（玩家 tp 到 60 格外，距离>32 触发 calmDown）后：vic/n1/n2 全 NONE。
"""
import json
import re
import socket
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon

DIM = "minecraft:the_nether"
PX, PY, PZ = 100.5, 70, 100.5

ROLES = ["vic", "n1", "n2", "nk", "s1"]
ANCHORS = {
    "vic": (102.5, 70, 100.5),
    "n1":  (102.5, 70, 98.5),
    "n2":  (102.5, 70, 102.5),
    "nk":  (104.5, 70, 100.5),
    "s1":  (102.5, 70, 94.5),
}


def in_nether(cmd):
    return server_rcon(f"execute in {DIM} run {cmd}")


# ── PAL 愤怒探针 ───────────────────────────────────────────

def pal(method, params=None):
    req = {"jsonrpc": "2.0", "method": "method_placeholder", "params": {}, "id": 1}
    req["method"] = method
    if params:
        req["params"] = params
    s = socket.create_connection(("192.0.2.10", 25585), timeout=5)
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
        return r.get("result") if "result" in r else str(r.get("error"))
    finally:
        s.close()


def anger(name):
    r = pal("mob.anger", {"name": name})
    if not isinstance(r, str):
        return None, None
    s = re.search(r"source=(\w+)", r)
    t = re.search(r"target=([\w.]+)", r)
    return (s.group(1) if s else None), (t.group(1) if t else None)


# ── 清理（每个 kill 单独发 + 确认消失）────────────────────

def kill_role(nm):
    in_nether(f"kill @e[name={nm}]")


def clear_all_roles():
    for nm in ROLES:
        kill_role(nm)
    time.sleep(0.5)
    # 确认五个角色都已不在（execute if entity）
    gone = True
    for nm in ROLES:
        r = in_nether(f"execute if entity @e[name={nm}]")
        if "passed" in r:
            # 再杀一次
            in_nether(f"kill @e[name={nm}]")
            gone = False
    time.sleep(0.4)
    return gone


def pull(names):
    for nm in names:
        x, y, z = ANCHORS[nm]
        in_nether(f"tp @e[name={nm}] {x} {y} {z}")


def spawn_round(victim, kin, nonkin, with_second_ring):
    clear_all_roles()
    layout = [("vic", victim), ("n1", kin), ("n2", kin), ("nk", nonkin)]
    if with_second_ring:
        layout.append(("s1", kin))
    for nm, type_id in layout:
        x, y, z = ANCHORS[nm]
        in_nether(f"summon {type_id} {x} {y} {z} "
                  f"{{CustomName:'\"{nm}\"',PersistenceRequired:1b}}")
    time.sleep(1.5)
    names = ["vic", "n1", "n2", "nk"] + (["s1"] if with_second_ring else [])
    # 确认每个角色都生成成功（探针能查到）
    for nm in names:
        if anger(nm)[0] is None:
            raise RuntimeError(f"{nm} 生成失败/探针查不到")
    return names


def ensure_alive_platform():
    if "死亡 是" in rpc("player.state"):
        rpc("player.respawn")
        time.sleep(2.5)
    in_nether(f"tp Dev {PX} {PY} {PZ} -90 0")
    for _ in range(2):
        server_rcon("effect give Dev minecraft:instant_health")
        time.sleep(0.7)


# ── 一轮 ─────────────────────────────────────────────────

def run_round(victim, kin, nonkin, with_second_ring, label):
    print(f"\n========== {label}：victim={victim} kin={kin} nonkin={nonkin} ==========")
    ensure_alive_platform()
    names = spawn_round(victim, kin, nonkin, with_second_ring)
    pull(names)

    print("攻击前基线:", {n: anger(n)[0] for n in names})

    key = victim.split(":")[1]
    print("攻击:", rpc("player.attack", {"target": key}).replace("\n", " "))

    # 保持几何 3s
    t0 = time.time()
    while time.time() - t0 < 3.0:
        pull(names)
        time.sleep(0.8)

    state = {n: anger(n) for n in names}
    for n in names:
        print(f"   {n}: source={state[n][0]} target={state[n][1]}")

    ok_vic = state["vic"] == ("PLAYER_DIRECT", "player")
    ok_n1 = state["n1"] == ("KIN_ALERT", "player")
    ok_n2 = state["n2"] == ("KIN_ALERT", "player")
    ok_nk = state["nk"][0] == "NONE"
    ok_s1 = (state["s1"][0] == "NONE") if with_second_ring else True
    alert_ok = ok_vic and ok_n1 and ok_n2 and ok_nk and ok_s1
    print(f"示警判定: victim={ok_vic} n1={ok_n1} n2={ok_n2} "
          f"异族不示警={ok_nk} 单层={ok_s1} → {'✓' if alert_ok else '✗'}")

    # 脱战：治疗后 tp 玩家 60 格远，拉锚点保持距离>32
    server_rcon("effect give Dev minecraft:instant_health")
    time.sleep(0.5)
    in_nether("tp Dev 100.5 70 160.5")
    t0 = time.time()
    while time.time() - t0 < 4.0:
        pull(names)
        time.sleep(0.6)

    after = {n: anger(n)[0] for n in names}
    print("脱战后:", after)
    calm_ok = (after["vic"] == "NONE" and after["n1"] == "NONE"
               and after["n2"] == "NONE" and after["nk"] == "NONE")
    print("脱战判定:", "✓ 全回中立（Brain 攻击记忆已擦）" if calm_ok else "✗ 残留仇恨")

    in_nether(f"tp Dev {PX} {PY} {PZ}")
    time.sleep(0.6)
    clear_all_roles()
    return alert_ok and calm_ok


def main():
    server_rcon("gamerule doMobSpawning false")
    try:
        a = run_round("minecraft:piglin", "minecraft:piglin",
                      "minecraft:hoglin", True, "轮1 猪灵（NeutralMob）")
        b = run_round("minecraft:hoglin", "minecraft:hoglin",
                      "minecraft:piglin", False, "轮2 疣猪兽（非NeutralMob）")
    finally:
        server_rcon("gamerule doMobSpawning true")
        server_rcon("effect give Dev minecraft:instant_health")

    print("\n==================== 总结 ====================")
    print("猪灵示警+单层+脱战:", "✓" if a else "✗")
    print("疣猪兽示警+脱战    :", "✓" if b else "✗")
    ok = a and b
    print("总判定:", "✅ Brain 示警语义真机验证通过" if ok else "❌ 有失败项")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
