#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-ANGER-003 同族示警边界硬断言 v2 —— 地下基岩层隔离环境。

架构：
  - 客户端从 peace-and-love 项目起 (./gradlew :neoforge:runClient),
    mods/ 目录下同时装 peace-and-love (被测) + mc-client-rpc (RPC 接口)
  - 服务器 192.0.2.10:25565 部署最新 peace-and-love jar
  - 测试脚本通过 mc-client-rpc 的 RPC (25586) 操控客户端,
    通过 RCON (25575) 控制服务器

对比 verify_anger_kin_boundary_hard.py 的根因修复：
  1. 自然怪污染 → 地下 y=-60 造 20×6×20 密封石盒 + doMobSpawning=false
     (改地下而非高空,避免服务器反作弊 "floating too long" 踢玩家)
  2. 边界值贴线（kin_alert_radius=4.0，near 恰好 4 格会被实体碰撞箱
     中心距离 ±0.5 浮动影响）→ near=2 格（必中）、far=8 格（必不中）

判定方式：execute on target + armor_stand marker 副作用（不依赖 RCON 回显）。
清理：kill 所有测试实体、填掉石盒、恢复 doMobSpawning=true（幂等）。

用法：
    python scripts/verify_anger_kin_boundary_v2.py
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import (
    Step, rpc, rpc_ok, server_rcon, wait_until,
)

PLAYER = "Dev"
# target 放玩家旁 0.5 格(必最近),near 放 3 格(必示警),far 放 8 格(必不示警)
# 关键:target 必须比 near 近,否则 attackNearest 会误瞄准 near
TARGET_DIST = 0.5
NEAR_DIST = 3   # 必被示警（< 4.0 半径）
FAR_DIST = 8    # 必不被示警（>> 4.0 半径）

# 客户端工程目录:peace-and-love(加载 pal mod + mc-client-rpc mod)
PAL_DIR = Path(r"D:\Coding\projects\peace-and-love")

PAL_RPC = ("192.0.2.10", 25585)
_pal_seq = [0]


def pal(method, params=None):
    _pal_seq[0] += 1
    req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": _pal_seq[0]}
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

# attach 模式:复用已启动的客户端(脚本不启动/不杀进程)
_attach_mode = "--attach" in sys.argv


# ── 客户端生命周期 ─────────────────────────────────────────────
_gradlew_proc: subprocess.Popen | None = None


def start_client() -> None:
    """从 peace-and-love 起客户端(同时加载 pal + mc-client-rpc)。"""
    global _gradlew_proc
    gradlew = str(PAL_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew"))
    _gradlew_proc = subprocess.Popen(
        [gradlew, ":neoforge:runClient"],
        cwd=str(PAL_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_client() -> None:
    """关闭客户端(尽力而为)。"""
    global _gradlew_proc
    try:
        rpc("client.disconnect", timeout=2)
    except Exception:
        pass
    if _gradlew_proc is not None:
        try:
            _gradlew_proc.terminate()
            _gradlew_proc.wait(timeout=10)
        except Exception:
            try:
                _gradlew_proc.kill()
            except Exception:
                pass
        _gradlew_proc = None


def _status_safe() -> dict | None:
    """安全拿 client.status（结构化 dict），客户端未就绪时返回 None（不抛异常）。"""
    try:
        return rpc("client.status", timeout=3)
    except Exception:
        return None


def _in_world() -> bool:
    st = _status_safe()
    return bool(st and st["inWorld"])


def _player_pos_safe() -> tuple[int, int, int]:
    """拿玩家位置(整数)，未进世界返回 (0,0,0)。player.pos 为结构化 dict。"""
    try:
        pos = rpc("player.pos", timeout=3)
        return int(pos["x"]), int(pos["y"]), int(pos["z"])
    except Exception:
        pass
    return 0, 0, 0


def _player_pos_safe_float() -> tuple[float, float, float]:
    """拿玩家位置(浮点)，未进世界返回 (0.0,0.0,0.0)。player.pos 为结构化 dict。"""
    try:
        pos = rpc("player.pos", timeout=3)
        return float(pos["x"]), float(pos["y"]), float(pos["z"])
    except Exception:
        pass
    return 0.0, 0.0, 0.0


def main() -> int:
    step = Step()
    started = False
    mob_spawning_changed = False
    try:
        # ── 1. 客户端进世界 ─────────────────────────────────────
        if _attach_mode:
            step.info("attach 模式:复用已启动客户端")
            if not rpc_ok("client.status", timeout=3):
                raise RuntimeError("attach 但 RPC 未就绪(客户端没在跑?)")
            started = False  # 不在 finally 里 kill
        else:
            step.info("启动客户端…")
            start_client()
            started = True
            # 先等 RPC 服务起来(首次构建 runClient 慢,给 240s)
            ok = wait_until(
                lambda: rpc_ok("client.status", timeout=3),
                timeout=240, interval=3, desc="RPC 就绪",
            )
            if not ok:
                raise RuntimeError("RPC 就绪超时(240s)")
        step.ok("客户端 RPC 就绪")

        # 跳无障碍引导屏 + 连服务器
        if _attach_mode:
            # attach 模式:玩家应该已在世界里(或在 TitleScreen)。先查状态。
            if not _in_world():
                # 不在世界里,尝试 connect
                step.info("attach 模式但不在世界,尝试 connect…")
                rpc("client.toTitle")
                rpc("client.connect", {"host": "192.0.2.10", "port": 25565})
                ok = wait_until(
                    lambda: (_in_world(), ""),
                    timeout=60, interval=2, desc="进世界",
                )
                if not ok:
                    raise RuntimeError("attach connect 后进世界超时")
        else:
            rpc("client.toTitle")
            rpc("client.connect", {"host": "192.0.2.10", "port": 25565})
            ok = wait_until(
                lambda: (_in_world(), ""),
                timeout=60, interval=2, desc="进世界",
            )
            if not ok:
                raise RuntimeError("进世界超时(60s)")
        step.ok("已进世界")

        st = rpc("player.state")
        if st["dead"]:
            rpc("player.respawn")
            time.sleep(1)
        step.ok("客户端已进世界")

        # ── 2. 关刷怪 + 清场 ────────────────────────────────────
        step.info("关闭自然刷怪 + 清场(kill 周围 40 格所有非玩家实体)…")
        server_rcon("gamerule doMobSpawning false")
        mob_spawning_changed = True
        # 清场:kill 玩家周围 40 格所有非玩家实体
        server_rcon(f"kill @e[type=!player,distance=..40]")
        time.sleep(1)
        step.ok("清场完成")

        # ── 3. 召唤三只测试怪(在玩家当前位置)────────────────────
        step.info(f"召唤 target/near({NEAR_DIST}格)/far({FAR_DIST}格)…")
        px, py, pz = _player_pos_safe()
        if px == 0 and py == 0 and pz == 0:
            raise RuntimeError("拿不到玩家位置")
        step.info(f"玩家位置: ({px}, {py}, {pz})")
        # 沿 +x 铺一条石头平台(py-1 层,宽 3),保证三怪同平面不坠崖。
        server_rcon(
            f"fill {px-1} {py-1} {pz-1} {px+FAR_DIST+2} {py-1} {pz+1} minecraft:stone"
        )
        # 关键：先把玩家锚定到确定的块中心，否则整数截断的召唤坐标会相对
        # 玩家真实亚格位置整体错位（实测攻击 dist=1.7 而非设计值，near 因此超 4 格）。
        server_rcon(f"tp Dev {px+0.5} {py} {pz+0.5}")
        time.sleep(1.0)
        # 僵尸是 A 类：示警走【原版 HurtByTargetGoal→alertOthers】（再由 mixin 收窄半径），
        # mod 不直接调 KinAlerter。因此绝不能加 NoAI——那会让 Goal 不运行、示警整条不发
        # （实测 NoAI 时 near=NONE）。召唤后立刻攻击：0.5s 内僵尸几乎不动，
        # target 距玩家 1.0（触及 3 内）、near 距 target 2.0（<4，示警，留 2 格裕量）、
        # far 距 target 7.0（>4，不示警，留 3 格裕量）。判定读 mod 的 AngerController 标记。
        nbt_base = "{PersistenceRequired:1b,CustomName:'\"%s\"'}"
        server_rcon(f"summon minecraft:zombie {px+1.5} {py} {pz+0.5} " + nbt_base % "target")
        server_rcon(f"summon minecraft:zombie {px+3.5} {py} {pz+0.5} " + nbt_base % "near")
        server_rcon(f"summon minecraft:zombie {px+8.5} {py} {pz+0.5} " + nbt_base % "far")
        time.sleep(0.6)
        step.ok("玩家已锚定块中心，三只测试怪就位")

        # ── 4. 玩家攻击 target（真实攻击,触发示警）───────────────
        # 贴身 player.attack 打 target（走真实攻击管线触发 hurt hook/KinAlerter）。
        # 不用 attackNearest：它会带着玩家寻路移动，污染后续判定。
        attack_result = None
        last_err = None
        for attempt in range(4):
            try:
                attack_result = rpc("player.attack", {"target": "zombie"}, timeout=8)
                break
            except RuntimeError as e:
                last_err = e
                step.info(f"player.attack 失败（重试）: {e}")
                time.sleep(1.2)
        if attack_result is None:
            raise RuntimeError(f"player.attack 多次失败: {last_err}")
        step.info(f"player.attack: hit={attack_result['hit']} dist={attack_result['distance']}")
        if not attack_result.get("hit"):
            raise RuntimeError("攻击未命中 target，示警判定无意义")

        # 等示警分发（KinAlerter 同步处理，给足余量）
        time.sleep(1.5)

        # ── 5. 判定：直接读 mod 的 AngerController 标记 ───────────
        # 不看怪是否移动（NoAI 本就不动，且玩家移动会污染相对位移）。
        s_t = anger_source("target")
        s_n = anger_source("near")
        s_f = anger_source("far")
        step.info(f"anger target={s_t} near={s_n} far={s_f}")
        if not (s_t == "PLAYER_DIRECT" and s_n == "KIN_ALERT" and s_f == "NONE"):
            raise RuntimeError(
                f"示警边界不符：target={s_t}(应PLAYER_DIRECT) "
                f"near={s_n}(应KIN_ALERT) far={s_f}(应NONE)")
        step.ok(f"硬断言通过：target 直接仇恨 / {NEAR_DIST} 格被示警 / {FAR_DIST} 格未示警")
        return 0
    finally:
        # ── 清理（幂等）─────────────────────────────────────────
        # kill 测试怪(target/near/far)
        try:
            server_rcon("kill @e[name=target]")
            server_rcon("kill @e[name=near]")
            server_rcon("kill @e[name=far]")
        except Exception as e:
            print(f"[cleanup] kill 测试实体失败: {e}")
        if mob_spawning_changed:
            try:
                server_rcon("gamerule doMobSpawning true")
            except Exception as e:
                print(f"[cleanup] 恢复 doMobSpawning 失败: {e}")
        if started:
            stop_client()


if __name__ == "__main__":
    raise SystemExit(main())
