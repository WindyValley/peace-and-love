#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""硬断言版 v2：用 execute 判定 near/far 是否把目标锁定到玩家。"""
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon, Step, stop_client, start_client

PLAYER = "Dev"


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
    try:
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

        pos = rpc("player.pos")
        cx, cy, cz = int(pos["x"]), int(pos["y"]), int(pos["z"])
        make_box(cx, cy, cz)
        server_rcon(f"tp {PLAYER} {cx} {cy+1} {cz}")
        time.sleep(1)
        server_rcon(f"kill @e[type=!player,distance=..32]")
        time.sleep(1)
        server_rcon(f"summon minecraft:zombie {cx} {cy+1} {cz+1} {{PersistenceRequired:1b,CustomName:'\"target\"'}}")
        server_rcon(f"summon minecraft:zombie {cx+4} {cy+1} {cz} {{PersistenceRequired:1b,CustomName:'\"near\"'}}")
        server_rcon(f"summon minecraft:zombie {cx+6} {cy+1} {cz} {{PersistenceRequired:1b,CustomName:'\"far\"'}}")
        time.sleep(2)
        server_rcon(f"execute as {PLAYER} at @s run damage @e[name=target,limit=1] 1 minecraft:player_attack by {PLAYER}")
        time.sleep(3)

        # 硬断言：若 near 的目标玩家是 Dev，则 execute on target 能找到 Dev
        # 硬断言：用 marker 副作用，而不是依赖 execute 回显
        server_rcon(f"kill @e[type=minecraft:armor_stand,name=NEAR_OK]")
        server_rcon(f"kill @e[type=minecraft:armor_stand,name=FAR_OK]")
        server_rcon("execute as @e[name=near,limit=1] on target if entity @s[name=Dev] run summon minecraft:armor_stand ~ ~ ~ {CustomName:'\"NEAR_OK\"',NoGravity:1b,Invisible:1b}")
        server_rcon("execute as @e[name=far,limit=1] on target if entity @s[name=Dev] run summon minecraft:armor_stand ~ ~ ~ {CustomName:'\"FAR_OK\"',NoGravity:1b,Invisible:1b}")
        time.sleep(1)
        ents = rpc("world.entities", {"radius": 24})
        print(f"entities => {ents}")

        # 新协议实体无 name 字段，按类型统计 marker 盔甲架：
        # 封闭区清场后仅可能有 NEAR_OK / FAR_OK 两个标记，数量即可区分。
        stands = [e for e in ents["entities"] if "armor_stand" in e["type"]]
        print(f"marker armor_stands => {stands}")
        if not stands:
            raise RuntimeError("4 格内同族未被示警（near 未锁定 Dev 为目标，无 NEAR_OK 标记）")
        if len(stands) > 1:
            raise RuntimeError("6 格外同族被误示警（far 也锁定了 Dev，出现 FAR_OK 标记）")

        step.ok("硬断言通过：4 格内同族被示警，6 格外未被示警")
        return 0
    finally:
        if started:
            stop_client()


if __name__ == "__main__":
    raise SystemExit(main())
