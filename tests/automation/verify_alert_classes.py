#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T-ALERT 同族示警三对照真机验证（复用原版 alertOthers 改造后）。

对照：
  A  zombie     原生有示警：玩家攻击后 near(3) 示警、far(8) 不应再被示警（原版35格已收窄到4）
  B  skeleton   原生无示警：玩家攻击后 near(3) 应【新增】示警、far(8) 不示警
  C  slime      无HurtBy且非Pathfinder：玩家攻击后 near(3) 应【新增】示警、far(8) 不示警

判定通道（已实测可靠）：
  execute as @e[name=near] on target run summon marker
  → near 当前 target 非 null（清场后只能是玩家 Dev）才会在 target 处生成 marker
  execute if entity @e[type=marker,tag=...]  → Test passed/failed

真实攻击：mc-client-rpc player.attackNearest（自动寻路+真实攻击管线），
不走 /damage（伪玩家攻击不触发 hurt mixin）。

用法：
  python verify_alert_classes.py            # 客户端已在世界
  python verify_alert_classes.py zombie     # 只测一种
"""
import re
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon

NEAR_DIST = 3          # < kin_alert_radius(4)，应示警（碰撞箱±0.5后 3.5<4）
FAR_DIST = 8           # > 4，不应示警（8-0.5>4）
TARGET_DIST = 1        # target 贴玩家，attackNearest 几乎不移动玩家
CLEAR_RADIUS = 40

# (显示名, 召唤实体类型id, attackNearest 的 target 参数, 额外NBT)
CASES = [
    ("A zombie(原生示警-应收窄)", "zombie", "zombie", ""),
    ("B skeleton(新增示警)", "skeleton", "skeleton", ""),
    ("C slime(无Goal-直调示警)", "slime", "slime", "{Size:1}"),
]


def log(*a):
    print(*a, flush=True)


def player_xyz():
    pos = rpc("player.pos")
    m = re.search(r"\((-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\)", pos)
    if not m:
        raise RuntimeError(f"解析玩家位置失败: {pos}")
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def entity_pos(name):
    """data get entity Pos → (x,y,z) 或 None。"""
    out = server_rcon(f"data get entity @e[name={name},limit=1] Pos")
    m = re.search(r"\[([-\d.]+)d,\s*([-\d.]+)d,\s*([-\d.]+)d\]", out)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def entity_hp(name):
    out = server_rcon(f"data get entity @e[name={name},limit=1] Health")
    m = re.search(r"([\d.]+)f?", out)
    return float(m.group(1)) if m else None


def has_dev_target(name, tag):
    """该命名生物当前是否有 target（清场后 target 只能是玩家）。"""
    server_rcon(f"kill @e[type=marker,tag={tag}]")
    # on target：执行上下文切到该生物的 target；target 为 null 时整条失败，不 summon
    server_rcon(
        f"execute as @e[name={name},limit=1] on target run "
        f"summon marker ~ ~ ~ {{Tags:[\"{tag}\"]}}")
    chk = server_rcon(f"execute if entity @e[type=marker,tag={tag}]")
    server_rcon(f"kill @e[type=marker,tag={tag}]")
    return "passed" in chk.lower() or "successful" in chk.lower() or "Test passed" in chk


def run_case(label, summon_type, attack_type, extra_nbt):
    log("\n" + "=" * 64)
    log(f"对照 {label}")
    log("=" * 64)

    # 清掉上一轮残留
    for n in ("target", "near", "far"):
        server_rcon(f"kill @e[name={n}]")
    server_rcon("kill @e[type=marker]")
    time.sleep(0.5)

    px, py, pz = player_xyz()
    log(f"玩家位置 ({px:.1f},{py:.1f},{pz:.1f})")

    # 沿 +x 铺石头平台（py-1 层），宽3，远到 far+2，保证三只同平面
    server_rcon(
        f"fill {int(px)-1} {int(py)-1} {int(pz)-1} "
        f"{int(px)+FAR_DIST+2} {int(py)-1} {int(pz)+1} minecraft:stone replace air")

    def summon(name, dx):
        cmd = (f"summon {summon_type} {int(px)+dx} {int(py)} {int(pz)} "
               f"{{CustomName:'{{\"text\":\"{name}\"}}',PersistenceRequired:1b{',' + extra_nbt[1:-1] if extra_nbt else ''}}}")
        server_rcon(cmd)

    summon("target", TARGET_DIST)
    summon("near", NEAR_DIST)
    summon("far", FAR_DIST)
    time.sleep(1.0)  # 落地，减少漂移

    for n in ("target", "near", "far"):
        log(f"  {n}: {entity_pos(n)} HP={entity_hp(n)}")

    # 攻击前：三只都不该有 target
    pre_near = has_dev_target("near", "pre_near")
    pre_far = has_dev_target("far", "pre_far")
    log(f"攻击前 target: near={pre_near} far={pre_far}（都应为 False）")

    # 真实攻击 target
    log(f"player.attackNearest {attack_type} ...")
    res = rpc("player.attackNearest", {"target": attack_type})
    log(f"  => {res}")
    time.sleep(1.0)

    hp = entity_hp("target")
    log(f"target 剩余血量 {hp}")
    hit = hp is not None and hp < 20.0
    if not hit:
        log("  ⚠ target 未掉血（可能挥空/冷却），本对照存疑")

    # 攻击后判定
    near_alert = has_dev_target("near", "post_near")
    far_alert = has_dev_target("far", "post_far")
    log(f"攻击后示警: near={near_alert} far={far_alert}")

    # 清理本对照
    for n in ("target", "near", "far"):
        server_rcon(f"kill @e[name={n}]")

    ok = (near_alert and not far_alert and not pre_near and not pre_far)
    log(f"结果: {'✅ PASS' if ok else '❌ FAIL'}（near应示警={near_alert}, far不应示警={not far_alert}, 命中={hit}）")
    return {"label": label, "hit": hit, "near": near_alert, "far": far_alert, "pass": ok}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    cases = [c for c in CASES if (not only or only in c[1])]

    log("[setup] 关闭自然生成 + 清场")
    server_rcon("gamerule doMobSpawning false")
    server_rcon(f"kill @e[type=!player,distance=..{CLEAR_RADIUS}]")
    time.sleep(1)

    results = []
    try:
        for c in cases:
            results.append(run_case(*c))
            time.sleep(1.5)
    finally:
        log("\n[teardown] 恢复自然生成 + 清场")
        server_rcon(f"kill @e[type=!player,distance=..{CLEAR_RADIUS}]")
        server_rcon("gamerule doMobSpawning true")

    log("\n" + "=" * 64)
    log("汇总")
    log("=" * 64)
    allok = True
    for r in results:
        log(f"  {'✅' if r['pass'] else '❌'} {r['label']}: "
            f"命中={r['hit']} near示警={r['near']} far不示警={not r['far']}")
        allok = allok and r["pass"]
    log("\n总体:", "✅ 全部通过" if allok else "❌ 存在失败")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
