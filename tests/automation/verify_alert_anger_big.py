#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大碰撞箱 C 类验证（NoAI 开放平台版）：elder_guardian / giant / ghast / phantom。

NoAI:1b 怪固定不动，无需隔间；平台召唤，距离精确。
判定走 mob.anger（KIN_ALERT 标记），同 verify_alert_guardian_v3。
用法：python verify_alert_anger_big.py <type>
"""
import json
import re
import socket
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon

TYPE = sys.argv[1]
EXTRA = sys.argv[2] if len(sys.argv) > 2 else ""
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
        return None
    return re.search(r"source=(\w+)", r).group(1)


def player_xyz():
    # 新协议：player.pos 返回结构化 dict {x,y,z,...}（float）
    p = rpc("player.pos")
    return float(p["x"]), float(p["y"]), float(p["z"])


def hp(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] Health")
    m = re.search(r"([\d.]+)f?", out)
    return float(m.group(1)) if m else None


def pos(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] Pos")
    m = re.search(r"\[([-\d.]+)d,\s*([-\d.]+)d,\s*([-\d.]+)d\]", out)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3))) if m else None


def do_attack(target, tries=3):
    """player.attackNearest：新协议成功返回结构化对象，错误 raise。
    超距(-32003)/忙(-32004) 可重试；无目标(-32002) 不重试直接抛。"""
    last = None
    for i in range(tries):
        try:
            return rpc("player.attackNearest", {"target": target})
        except RuntimeError as e:
            last = e
            msg = str(e)
            if "[-32003]" in msg or "[-32004]" in msg:
                time.sleep(1.5 * (i + 1))
                continue
            raise
    raise last


def summon(name, x, y, z):
    extra = ("," + EXTRA[1:-1]) if EXTRA else ""
    server_rcon(f"summon {TYPE} {x} {y} {z} "
                f"{{CustomName:'{{\"text\":\"{name}\"}}',PersistenceRequired:1b,NoAI:1b{extra}}}")


def main():
    server_rcon("gamerule doMobSpawning false")
    server_rcon("kill @e[type=!player,distance=..80]")
    for n in ("target", "near", "far"):
        server_rcon(f"kill @e[name={n}]")
    time.sleep(1)

    px, py, pz = player_xyz()
    ix, iy, iz = int(round(px)), int(round(py)), int(round(pz))
    log(f"=== {TYPE} === ({ix},{iy},{iz})")
    try:
        # 宽平台，三怪 NoAI 定点：target +1 / near +3（距 target 2）/ far +9（距 target 8）
        server_rcon(f"fill {ix-2} {iy-1} {iz-4} {ix+11} {iy-1} {iz+4} stone")
        summon("target", ix + 1, iy, iz)
        summon("near", ix + 3, iy, iz)
        summon("far", ix + 9, iy, iz)
        time.sleep(1.5)

        tp, np_ = pos("target"), pos("near")
        d = ((tp[0]-np_[0])**2 + (tp[2]-np_[2])**2) ** 0.5
        log(f"  target={tp} HP={hp('target')}  near距={d:.2f}  farHP={hp('far')}")
        log(f"  攻击前: {{t={anger('target')} n={anger('near')} f={anger('far')}}}")

        hp0 = hp("target")
        res = do_attack(TYPE)
        log("attack ->", f"hit={res['hit']} dist={res['distance']} reach={res['reach']} "
            f"hp {res['hpBefore']}->{res['hpAfter']}")
        time.sleep(1.0)
        post = {n: anger(n) for n in ("target", "near", "far")}
        log(f"  targetHP {hp0}->{hp('target')}  攻击后: {post}")

        ok = post["target"] == "PLAYER_DIRECT" and post["near"] == "KIN_ALERT" \
            and post["far"] == "NONE" and d < 4
        log("结果:", f"✅ PASS（{TYPE}）" if ok else "❌ FAIL")
        sys.exit(0 if ok else 1)
    finally:
        for n in ("target", "near", "far"):
            server_rcon(f"kill @e[name={n}]")
        server_rcon("kill @e[type=!player,distance=..80]")
        # 平台地板保留（拆除会让站立的玩家踩空掉线）；只清上方残块
        server_rcon(f"fill {ix-2} {iy} {iz-4} {ix+11} {iy+2} {iz+4} air")
        server_rcon("gamerule doMobSpawning true")


if __name__ == "__main__":
    main()
