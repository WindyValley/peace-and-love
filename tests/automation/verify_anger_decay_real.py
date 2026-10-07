#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「脱战后怪物恢复中立」。两条脱战规则都真机验证：

  A. 时间到：临时把仇恨持续时间改成 5 秒，玩家打一拳后，
     3 秒时应仍在仇恨，7 秒时应恢复中立
  B. 玩家走远：临时把脱战距离改成 6 格、仇恨时长给足 60 秒，
     打一拳后把玩家送到 10 格外，怪物应恢复中立

判定走被测 mod 的 mob.anger 探针：
  攻击后 source=PLAYER_DIRECT；脱战后 source=NONE。

手法沿用验证过的可靠模式：玩家用 tp 封进固定隔间，
攻击用 player.attackNearest；配置开始前备份、finally 恢复。
"""
import json
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon

SSH_TARGET = "mc@192.0.2.10"
REMOTE_DIR = "/home/mc/minecraft"
CFG = f"{REMOTE_DIR}/config/peaceandlove.json"
BAK = f"{REMOTE_DIR}/config/peaceandlove.json.verify_bak"
PAL_RPC = ("192.0.2.10", 25585)
_id = [0]


def log(*a):
    print(*a, flush=True)


def ssh_run(cmd, timeout=30):
    r = subprocess.run(["ssh", SSH_TARGET, cmd],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ssh 失败: {cmd}\n{r.stderr}")
    return r.stdout


def set_config_value(key, value):
    val = str(value)
    ssh_run(
        f"sed -i -E 's|\"{key}\"[[:space:]]*:[[:space:]]*[^,}}]+|\"{key}\": {val}|' {CFG}")
    server_rcon("pal reload")
    time.sleep(0.5)


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
    if not isinstance(r, str):
        return None
    m = re.search(r"source=(\w+)", r)
    return m.group(1) if m else None


def hp(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] Health")
    m = re.search(r"([\d.]+)f?", out)
    return float(m.group(1)) if m else None


def build_arena(ix, iy, iz):
    """玩家隔间(ix) + target 隔间(ix+1) 连体石壳，玩家朝东 1 格打 target。
    东边预留空地，方便 B 项把玩家送远。"""
    # 地板：玩家/目标 + 东边到 ix+13
    server_rcon(f"fill {ix-2} {iy-1} {iz-1} {ix+13} {iy-1} {iz+1} stone")
    # 连体壳：玩家+目标 宽 2、高 3
    server_rcon(f"fill {ix-1} {iy-1} {iz-1} {ix+2} {iy+2} {iz+1} stone")
    server_rcon(f"fill {ix} {iy} {iz} {ix+1} {iy+1} {iz} air")


def summon_target(ix, iy, iz):
    server_rcon("kill @e[name=dtarget]")
    server_rcon(
        f"summon zombie {ix+1} {iy} {iz} "
        f"{{CustomName:'{{\"text\":\"dtarget\"}}',PersistenceRequired:1b,NoAI:1b}}")


def attack_target():
    """封进玩家隔间，attackNearest 直到 PLAYER_DIRECT。"""
    return bool(rpc("player.attackNearest", {"target": "zombie"}))


def teardown_arena(ix, iy, iz):
    server_rcon("kill @e[name=dtarget]")
    server_rcon("kill @e[type=marker]")
    # 上部清空（保留 iy-1 地板）
    server_rcon(f"fill {ix-2} {iy} {iz-1} {ix+13} {iy+2} {iz+1} air")


def case_time_decay(ix, iy, iz):
    log("\n=== A. 时间到自动脱战（临时仇恨时长 5 秒）===")
    set_config_value("anger_cooldown_seconds", 5)
    try:
        build_arena(ix, iy, iz)
        server_rcon(f"tp Dev {ix+0.5} {iy} {iz+0.5}")
        time.sleep(0.5)
        summon_target(ix, iy, iz)
        time.sleep(0.8)
        if not attack_target():
            log("  ❌ attackNearest 失败，本项无效")
            return False
        time.sleep(0.5)
        src0 = anger_source("dtarget")
        log(f"  攻击命中，source={src0}（应 PLAYER_DIRECT）")
        if src0 != "PLAYER_DIRECT":
            log("  ❌ 攻击后未进仇恨，本项无效")
            return False

        time.sleep(3)
        src3 = anger_source("dtarget")
        time.sleep(4)
        src7 = anger_source("dtarget")
        log(f"  攻击后 3s: source={src3}（应 PLAYER_DIRECT）")
        log(f"  攻击后 7s: source={src7}（应 NONE）")
        ok = src3 == "PLAYER_DIRECT" and src7 == "NONE"
        log("  结果:", "✅ PASS" if ok else "❌ FAIL")
        return ok
    finally:
        teardown_arena(ix, iy, iz)


def case_distance_decay(ix, iy, iz):
    log("\n=== B. 玩家走远脱战（临时脱战距离 6 格，时长 60 秒）===")
    set_config_value("anger_cooldown_seconds", 60)
    set_config_value("anger_cooldown_distance", 6)
    try:
        build_arena(ix, iy, iz)
        server_rcon(f"tp Dev {ix+0.5} {iy} {iz+0.5}")
        time.sleep(0.5)
        summon_target(ix, iy, iz)
        time.sleep(0.8)
        if not attack_target():
            log("  ❌ attackNearest 失败，本项无效")
            return False
        time.sleep(0.5)
        src0 = anger_source("dtarget")
        log(f"  攻击命中，source={src0}（应 PLAYER_DIRECT）")
        if src0 != "PLAYER_DIRECT":
            log("  ❌ 攻击后未进仇恨，本项无效")
            return False

        # 送到目标东侧 10 格（落点地板已铺），同高度短距离 tp
        far_x = ix + 11
        server_rcon(f"tp Dev {far_x+0.5} {iy} {iz+0.5}")
        time.sleep(2.0)   # 脱战判定每 tick 跑，等它处理

        # 确认玩家确实在远处
        m = re.search(r"\((-?[\d.]+),", rpc("player.pos"))
        px_now = float(m.group(1))
        dist = abs(px_now - (ix + 1.5))
        log(f"  玩家现在 x={px_now:.1f}，距目标 {dist:.1f} 格")
        if dist < 8:
            log("  ❌ 玩家没送够远，本项无效")
            return False

        src = anger_source("dtarget")
        log(f"  远离后 source={src}（应 NONE）")
        ok = src == "NONE"
        log("  结果:", "✅ PASS" if ok else "❌ FAIL")
        return ok
    finally:
        teardown_arena(ix, iy, iz)
        # 玩家送回安全平台中心（永久平台 40,-57,23 一带有地板）
        server_rcon("tp Dev 40.5 -57 23.5")


def main():
    # 死亡检查
    if "死亡 是" in rpc("player.state"):
        rpc("player.respawn")
        time.sleep(2)

    log("备份服务器配置 ……")
    ssh_run(f"cp {CFG} {BAK}")
    server_rcon("gamerule doMobSpawning false")
    server_rcon("effect give Dev resistance 120 1 true")

    # 测试台原点：永久安全平台东侧外
    ix, iy, iz = 46, -57, 23
    ra = rb = False
    try:
        ra = case_time_decay(ix, iy, iz)
        rb = case_distance_decay(ix, iy, iz)
    finally:
        log("\n恢复原配置并热重载 ……")
        try:
            ssh_run(f"cp {BAK} {CFG} && rm -f {BAK}")
            server_rcon("pal reload")
            log("配置已恢复")
        except Exception as e:
            log(f"⚠️ 自动恢复失败，请手动：ssh {SSH_TARGET} \"cp {BAK} {CFG}\" 再 /pal reload。原因: {e}")
        server_rcon("gamerule doMobSpawning true")
        time.sleep(0.5)
        log("玩家状态:", rpc("player.state"))

    log("\n" + "=" * 50)
    log(f"A 时间到脱战: {'✅' if ra else '❌'}")
    log(f"B 走远脱战:   {'✅' if rb else '❌'}")
    sys.exit(0 if ra and rb else 1)


if __name__ == "__main__":
    main()
