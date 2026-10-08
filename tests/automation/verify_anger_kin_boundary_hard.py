#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""硬断言版：封闭区 + 直接读 AngerController 标记判定同族示警边界。"""
import json
import re
import socket
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon, Step, stop_client, start_client

PLAYER = "Dev"

_pal_seq = [0]


def pal(method, params=None):
    _pal_seq[0] += 1
    req = {"jsonrpc": "2.0", "method": method, "id": _pal_seq[0]}
    if params:
        req["params"] = params
    s = socket.create_connection(("192.0.2.10", 25585), timeout=5)
    s.sendall((json.dumps(req) + "\n").encode())
    buf = b""
    s.settimeout(5)
    try:
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    except socket.timeout:
        pass
    s.close()
    resp = json.loads(buf.decode().strip())
    if "error" in resp:
        raise RuntimeError(f"pal {method} 错误 {resp['error']}")
    return resp["result"]


def anger_source(name):
    r = pal("mob.anger", {"name": name})
    if not isinstance(r, str) or "source=" not in r:
        return None
    m = re.search(r"source=(\w+)", r)
    return m.group(1) if m else None


def make_box(cx: int, cy: int, cz: int) -> None:
    cmds = [
        f"fill {cx-8} {cy} {cz-8} {cx+8} {cy} {cz+8} minecraft:stone",
        f"fill {cx-8} {cy+6} {cz-8} {cx+8} {cy+6} {cz+8} minecraft:stone",
        f"fill {cx-8} {cy+1} {cz-8} {cx-8} {cy+5} {cz+8} minecraft:stone",
        f"fill {cx+8} {cy+1} {cz-8} {cx+8} {cy+5} {cz+8} minecraft:stone",
        f"fill {cx-8} {cy+1} {cz-8} {cx+8} {cy+5} {cz-8} minecraft:stone",
        f"fill {cx-8} {cy+1} {cz+8} {cx+8} {cy+5} {cz+8} minecraft:stone",
        f"fill {cx-7} {cy+1} {cz-7} {cx+7} {cy+5} {cz+7} minecraft:air",
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
        combat_loop_test._attach_mode = True  # stop_client 只断开、不杀常驻客户端
    try:
        if attach:
            step.info("attach 模式：复用常驻客户端")
            if not rpc("client.status")["inWorld"]:
                raise RuntimeError("attach 但未在世界中")
        else:
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

        pos = rpc("player.pos")
        px, py, pz = float(pos["x"]), float(pos["y"]), float(pos["z"])
        cx, cy, cz = int(px), int(py), int(pz)

        step.info("创建封闭测试区…")
        make_box(cx, cy, cz)
        server_rcon("gamerule doMobSpawning false")
        server_rcon("kill @e[type=!player]")
        time.sleep(1)

        # 沿 +x 铺平台 + 锚定玩家到块中心（几何确定，同 v2）。
        server_rcon(f"fill {cx-1} {cy-1} {cz-1} {cx+10} {cy-1} {cz+1} minecraft:stone")
        server_rcon(f"tp Dev {cx+0.5} {cy} {cz+0.5}")
        time.sleep(1.0)
        # 僵尸是 A 类：示警走原版 HurtByTargetGoal（NoAI 会禁掉，故不加）。
        # target 距玩家 1.0、near 距 target 2.0(<4)、far 距 target 7.0(>4)。
        nbt = "{PersistenceRequired:1b,CustomName:'\"%s\"'}"
        server_rcon(f"summon minecraft:zombie {cx+1.5} {cy} {cz+0.5} " + nbt % "target")
        server_rcon(f"summon minecraft:zombie {cx+3.5} {cy} {cz+0.5} " + nbt % "near")
        server_rcon(f"summon minecraft:zombie {cx+8.5} {cy} {cz+0.5} " + nbt % "far")
        time.sleep(0.6)

        # 真实玩家攻击 target。
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
        time.sleep(1.0)

        # 判定：直接读 mod 的仇恨来源标记。
        s_t = anger_source("target")
        s_n = anger_source("near")
        s_f = anger_source("far")
        step.info(f"anger target={s_t} near={s_n} far={s_f}")

        ok = s_t == "PLAYER_DIRECT" and s_n == "KIN_ALERT" and s_f == "NONE"
        if not ok:
            raise RuntimeError(
                f"示警边界不符：target={s_t}(应PLAYER_DIRECT) "
                f"near={s_n}(应KIN_ALERT) far={s_f}(应NONE)"
            )

        step.ok("硬断言通过：4 格内同族被示警，6 格外未被示警")
        return 0
    finally:
        if started:
            stop_client()


if __name__ == "__main__":
    raise SystemExit(main())
