#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「白名单热改后行为立即切换，改回来也立即恢复」。

白名单的含义：名单里的怪物保持原版敌对行为，模组不碰它
（不中立化、玩家打它也不进模组的仇恨/示警逻辑）。

三轮真机对照（每轮召唤一只僵尸打一拳，读 mob.anger 的 source）：
  1. 默认（僵尸不在名单）：source=PLAYER_DIRECT —— 模组在管
  2. /pal whitelist add zombie 后：source=NONE —— 模组不管了，保持原版
  3. /pal whitelist remove zombie 后：source=PLAYER_DIRECT —— 恢复
另外每步 ssh 查配置文件，确认改动确实写进了文件（不只是内存里）。
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


def whitelist_in_file():
    """配置文件的 hostile_whitelist 数组里有没有 zombie。"""
    out = ssh_run(f"python3 -c \"import json;d=json.load(open('{CFG}'));print('minecraft:zombie' in d['hostile_whitelist'])\"")
    return out.strip() == "True"


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


def build_arena(ix, iy, iz):
    server_rcon(f"fill {ix-1} {iy-1} {iz-1} {ix+2} {iy-1} {iz+1} stone")   # 地板
    server_rcon(f"fill {ix-1} {iy-1} {iz-1} {ix+2} {iy+2} {iz+1} stone")
    server_rcon(f"fill {ix} {iy} {iz} {ix+1} {iy+1} {iz} air")


def probe_round(ix, iy, iz, label):
    """建隔间 → 封玩家 → 召唤 NoAI 僵尸 → 打一拳 → 返回 source。"""
    server_rcon("kill @e[name=wtest]")
    build_arena(ix, iy, iz)
    server_rcon(f"tp Dev {ix+0.5} {iy} {iz+0.5}")
    time.sleep(0.5)
    server_rcon(
        f"summon zombie {ix+1} {iy} {iz} "
        f"{{CustomName:'{{\"text\":\"wtest\"}}',PersistenceRequired:1b,NoAI:1b}}")
    time.sleep(0.8)
    try:
        hit = rpc("player.attackNearest", {"target": "zombie"})
        time.sleep(0.6)
        src = anger_source("wtest")
        log(f"  [{label}] attackNearest={hit} source={src}")
        return src
    finally:
        server_rcon("kill @e[name=wtest]")
        server_rcon(f"fill {ix-1} {iy} {iz-1} {ix+2} {iy+2} {iz+1} air")


def main():
    if "死亡 是" in rpc("player.state"):
        rpc("player.respawn")
        time.sleep(2)
    server_rcon("gamerule doMobSpawning false")
    server_rcon("effect give Dev resistance 180 1 true")

    # 安全前提：开始时僵尸不能在名单里（在的话先移出）
    if whitelist_in_file():
        log("开始前僵尸已在名单，先移出")
        server_rcon("pal whitelist remove zombie")
        time.sleep(0.5)

    ix, iy, iz = 46, -57, 23
    results = []
    try:
        log("\n--- 第 1 轮：默认状态 ---")
        s1 = probe_round(ix, iy, iz, "默认")
        f1 = whitelist_in_file()
        log(f"  配置文件里有 zombie: {f1}（应 False）")
        r1 = (s1 == "PLAYER_DIRECT" and f1 is False)
        results.append(("默认: 模组在管", r1))

        log("\n--- 第 2 轮：把僵尸加入白名单 ---")
        out = server_rcon("pal whitelist add zombie")
        log(f"  命令回显: {out}")
        time.sleep(0.5)
        s2 = probe_round(ix, iy, iz, "白名单")
        f2 = whitelist_in_file()
        log(f"  配置文件里有 zombie: {f2}（应 True）")
        r2 = (s2 == "NONE" and f2 is True)
        results.append(("加入名单: 模组放手、改动已落盘", r2))

        log("\n--- 第 3 轮：移出白名单（回滚）---")
        out = server_rcon("pal whitelist remove zombie")
        log(f"  命令回显: {out}")
        time.sleep(0.5)
        s3 = probe_round(ix, iy, iz, "回滚")
        f3 = whitelist_in_file()
        log(f"  配置文件里有 zombie: {f3}（应 False）")
        r3 = (s3 == "PLAYER_DIRECT" and f3 is False)
        results.append(("移出名单: 立即恢复", r3))
    finally:
        # 兜底：确保僵尸不在名单
        try:
            server_rcon("pal whitelist remove zombie")
        except Exception:
            pass
        server_rcon("kill @e[name=wtest]")
        server_rcon("gamerule doMobSpawning true")
        server_rcon("tp Dev 40.5 -57 23.5")
        time.sleep(0.5)
        log("\n最终玩家状态:", rpc("player.state"))

    log("\n" + "=" * 50)
    allok = True
    for name, ok in results:
        log(f"{'✅' if ok else '❌'} {name}")
        allok = allok and ok
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
