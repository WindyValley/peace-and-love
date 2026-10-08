#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封闭区内验证：玩家攻击后，同族 4 格内应示警，6 格外不应示警。"""
import json
import re
import socket
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon, Step, stop_client, start_client

PLAYER = "Dev"
PAL_RPC = ("192.0.2.10", 25585)
_pal_id = [0]


def pal(method, params=None):
    _pal_id[0] += 1
    req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": _pal_id[0]}
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
    if not isinstance(r, str) or "source=" not in r:
        return None
    m = re.search(r"source=(\w+)", r)
    return m.group(1) if m else None


def make_box(cx: int, cy: int, cz: int) -> None:
    cmds = [
        f"fill {cx-6} {cy} {cz-6} {cx+6} {cy} {cz+6} minecraft:stone",
        f"fill {cx-6} {cy+5} {cz-6} {cx+6} {cy+5} {cz+6} minecraft:stone",
        f"fill {cx-6} {cy+1} {cz-6} {cx-6} {cy+4} {cz+6} minecraft:stone",
        f"fill {cx+6} {cy+1} {cz-6} {cx+6} {cy+4} {cz+6} minecraft:stone",
        f"fill {cx-6} {cy+1} {cz-6} {cx+6} {cy+4} {cz-6} minecraft:stone",
        f"fill {cx-6} {cy+1} {cz+6} {cx+6} {cy+4} {cz+6} minecraft:stone",
        f"fill {cx-5} {cy+1} {cz-5} {cx+5} {cy+4} {cz+5} minecraft:air",
    ]
    for c in cmds:
        server_rcon(c)


def wait_ready() -> None:
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            status = rpc("client.status", timeout=2)
            if status["inWorld"]:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("进世界超时")


def main() -> int:
    step = Step()
    started = False
    attach = "--attach" in sys.argv
    if attach:
        import combat_loop_test
        combat_loop_test._attach_mode = True
        step.info("attach 模式：复用常驻客户端")
    try:
        if not attach:
            step.info("启动客户端并进入世界…")
            start_client()
            started = True
            deadline = time.time() + 90
            while time.time() < deadline:
                try:
                    status = rpc("client.status", timeout=2)
                    if status:
                        break
                except Exception:
                    time.sleep(1)
            else:
                raise RuntimeError("客户端 RPC 就绪超时")

            rpc("client.toTitle")
            rpc("client.connect", {"host": "192.0.2.10", "port": 25565})
            wait_ready()

        st = rpc("player.state")
        if st["dead"]:
            rpc("player.respawn")
            time.sleep(1)

        # 先关刷怪 + 全场清场：清掉上一个脚本残留的敌对僵尸（attach 复用同一客户端，
        # 它们会一直追玩家）。不能用 distance=..16：RCON 无位置锚点，distance 相对
        # 世界出生点，在远离出生点的场地清不到任何东西。
        server_rcon("gamerule doMobSpawning false")
        server_rcon("kill @e[type=!player]")
        time.sleep(1)

        pos = rpc("player.pos")
        px, py, pz = float(pos["x"]), float(pos["y"]), float(pos["z"])
        cx, cy, cz = int(px), int(py), int(pz)

        step.info("创建封闭测试区…")
        make_box(cx, cy, cz)
        # 沿 +x 铺平到 far，保证三怪同平面（洞穴远处可能是空气）
        server_rcon(f"fill {cx-1} {cy-1} {cz-1} {cx+10} {cy-1} {cz+1} stone")
        server_rcon(f"tp {PLAYER} {cx+0.5} {cy} {cz+0.5}")
        time.sleep(1)

        step.info("召唤 target(1格)/near(3格)/far(8格)…")
        nbt = "{PersistenceRequired:1b,CustomName:'\"%s\"'}"
        server_rcon(f"summon minecraft:zombie {cx+1.5} {cy} {cz+0.5} " + nbt % "target")
        server_rcon(f"summon minecraft:zombie {cx+3.5} {cy} {cz+0.5} " + nbt % "near")
        server_rcon(f"summon minecraft:zombie {cx+8.5} {cy} {cz+0.5} " + nbt % "far")
        time.sleep(0.6)

        # 真实玩家攻击 target（/damage 不触发玩家攻击 hook，示警不会发生）。
        attacked = False
        for _try in range(4):
            try:
                atk = rpc("player.attack", {"target": "zombie"}, timeout=8)
                step.info(f"player.attack hit={atk['hit']} dist={atk['distance']}")
                attacked = True
                break
            except RuntimeError as e:
                step.info(f"攻击失败（重试）: {e}")
                time.sleep(1.2)
        if not attacked:
            raise RuntimeError("未能真实攻击 target，无法验证示警")
        time.sleep(1.5)

        # 判定走 mob.anger：near 应 KIN_ALERT，far 应 NONE，target 应 PLAYER_DIRECT
        s_t, s_n, s_f = (anger_source("target"), anger_source("near"), anger_source("far"))
        step.info(f"anger target={s_t} near={s_n} far={s_f}")
        if not (s_t == "PLAYER_DIRECT" and s_n == "KIN_ALERT" and s_f == "NONE"):
            raise RuntimeError(f"示警边界不符：target={s_t} near={s_n} far={s_f}")

        step.ok("同族示警边界验证通过：target 直接仇恨、near 被示警、far 不示警")
        return 0
    finally:
        if started:
            stop_client()


if __name__ == "__main__":
    raise SystemExit(main())
