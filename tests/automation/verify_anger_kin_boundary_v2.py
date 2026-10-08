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
import os
import re
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
        # 沿 +x 铺一条石头平台(py-1 层,宽 3),保证 target/near/far 同平面不坠崖。
        # 洞穴地形在远处可能是空气,不铺会导致 far 掉到下一层(垂直距离污染判定)。
        server_rcon(
            f"fill {px-1} {py-1} {pz-1} {px+FAR_DIST+2} {py-1} {pz+1} minecraft:stone"
        )
        # target 在玩家旁 1 格(必最近)、near 在 3 格、far 在 8 格
        # 注意:不能用 NoAI:1b(僵尸会失去 Goal,setTarget 无效)
        # 改用短 sleep(0.5s)减少生成后乱跑
        nbt_base = "{PersistenceRequired:1b,CustomName:'\"%s\"'}"
        server_rcon(
            f"summon minecraft:zombie {px+TARGET_DIST} {py} {pz} "
            + nbt_base % "target"
        )
        server_rcon(
            f"summon minecraft:zombie {px+NEAR_DIST} {py} {pz} "
            + nbt_base % "near"
        )
        server_rcon(
            f"summon minecraft:zombie {px+FAR_DIST} {py} {pz} "
            + nbt_base % "far"
        )
        time.sleep(0.5)  # 短 sleep,减少乱跑
        step.ok("三只测试怪已就位")

        # ── 4. 玩家攻击 target（真实攻击,触发示警）───────────────
        # 关键:用高级指令 player.attackNearest,自动寻路到触及范围再攻击。
        # 它走真实攻击管线(mc.gameMode.attack → ServerboundInteractPacket),
        # 触发服务端 LivingHurtEvent → LivingEntityHurtMixin → KinAlerter。
        # 区别于 damage 命令(伪玩家攻击,不触发 hurt 事件,示警无效)。
        step.info("玩家用 attackNearest 自动寻路攻击 target…")
        # 新协议：成功返回结构化对象，协议错误 raise RuntimeError（消息含 [code]）。
        # -32004 忙 / -32003 超距 / -32002 无目标 多为瞬时态，短暂等待后重试。
        attack_result = None
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                attack_result = rpc("player.attackNearest", {"target": "zombie"}, timeout=20)
                break
            except RuntimeError as e:
                last_err = e
                msg = str(e)
                if any(code in msg for code in ("[-32004]", "[-32003]", "[-32002]")):
                    step.info(f"attackNearest 第 {attempt+1} 次未完成（{msg}），等待后重试…")
                    time.sleep(2)
                    continue
                raise
        if attack_result is None:
            raise RuntimeError(f"attackNearest 三次均失败: {last_err}")
        step.info(f"attackNearest 返回: {attack_result}")
        if not attack_result.get("hit"):
            step.info("attackNearest 返回 hit=False，以服务端权威血量复核（可能血量同步滞后）")

        # 确认真实命中:target 掉血(从 20 下降)
        time.sleep(0.5)
        hp_raw = server_rcon("data get entity @e[name=target,limit=1] Health")
        m_hp = re.search(r"([\d.]+)f", hp_raw)
        target_hp = float(m_hp.group(1)) if m_hp else 20.0
        step.info(f"target 剩余血量: {target_hp}/20")
        if target_hp >= 20.0:
            raise RuntimeError("target 未掉血——攻击未命中服务端,示警判定无意义")

        # 攻击后强制玩家停止移动(attackNearest 寻路有惯性),等玩家完全站定。
        # 否则测量期间玩家滑行会抵消 near 的追击距离,污染行为信号。
        rpc("player.stop", timeout=3)
        time.sleep(1.5)

        # ── 5. 硬断言：示警行为信号 ────────────────────────────
        # 原理:被示警的 zombie(setTarget=Dev)会激活 MeleeAttackGoal 寻路追击玩家,
        # 未被示警的 zombie 无 target、原地闲置随机游荡(位移极小)。
        # 测攻击前/后 near、far 到玩家的距离变化(服务端 data get,权威)。
        step.info("测量 near/far 示警后是否追击玩家(行为信号)…")
        time.sleep(0.5)

        def entity_pos(name: str):
            raw = server_rcon(f"data get entity @e[name={name},limit=1] Pos")
            m = re.search(r"\[(-?[\d.]+)d?,?\s*(-?[\d.]+)d?,?\s*(-?[\d.]+)d?\]", raw)
            if not m:
                raise RuntimeError(f"解析 {name} 位置失败: {raw}")
            return float(m.group(1)), float(m.group(2)), float(m.group(3))

        def horiz_dist(a, b):
            return ((a[0]-b[0])**2 + (a[2]-b[2])**2) ** 0.5

        p0 = _player_pos_safe_float()
        n0 = entity_pos("near")
        f0 = entity_pos("far")
        d_near0 = horiz_dist(n0, p0)
        d_far0 = horiz_dist(f0, p0)
        step.info(f"攻击前: 玩家{p0} near{n0}({d_near0:.1f}格) far{f0}({d_far0:.1f}格)")

        # 观察 2.5s:被示警 zombie 会明显逼近(>1格),闲置 zombie 几乎不动
        time.sleep(2.5)
        p1 = _player_pos_safe_float()
        n1 = entity_pos("near")
        f1 = entity_pos("far")
        d_near1 = horiz_dist(n1, p1)
        d_far1 = horiz_dist(f1, p1)
        step.info(f"攻击后: 玩家{p1} near{n1}({d_near1:.1f}格) far{f1}({d_far1:.1f}格)")

        near_approach = d_near0 - d_near1  # 正=逼近玩家
        far_approach = d_far0 - d_far1
        step.info(f"near 逼近 {near_approach:+.2f} 格 / far 逼近 {far_approach:+.2f} 格")

        # near 必被示警:2.5s 内应明显追击(>1 格);far 必不示警:几乎不动(<1 格)
        if near_approach < 1.0:
            raise RuntimeError(
                f"{NEAR_DIST} 格内同族未被示警（near 未追击玩家，仅逼近 {near_approach:.2f} 格）"
            )
        if far_approach > 1.0:
            raise RuntimeError(
                f"{FAR_DIST} 格外同族被误示警（far 也在追击，逼近 {far_approach:.2f} 格）"
            )
        step.ok(f"硬断言通过：{NEAR_DIST} 格被示警(追击{near_approach:.1f}格) / {FAR_DIST} 格未示警({far_approach:+.1f}格)")
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
