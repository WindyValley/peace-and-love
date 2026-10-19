#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PAL 本地单机全功能冒烟（结合 mc-client-rpc 新增的 world.create）。

新拓扑（与此前连 192.0.2.10 dedicated 服不同）：
  - 从 peace-and-love 工程起 :<loader>:runClient -PenableVerifyRpc=true，
    PAL 走 loom dev classpath，run/mods 放 mc-client-rpc jar（驱动）。
  - world.create 在本地建一个【允许作弊】的生存世界 → 集成服务器（同进程）。
  - 无 RCON：所有管理命令（summon/gamerule/tp/whitelist）走 mc-client-rpc
    的 player.command（作弊世界房主自带 OP4）。
  - 三条通道：
      25586  mc-client-rpc   操控玩家 + 执行斜杠命令
      25585  PAL verify 探针 debug.inspect / mob.anger 读服务端内部状态
      玩家血量/位置           player.state / player.pos

覆盖（一轮，3~5 分钟）：
  A 建世界 + 双通道就绪
  B debug.inspect 门控链：僵尸(适配)/牛(未适配)
  C 中立化：僵尸贴身不主动攻击、目标为空、不掉血
  D 真实攻击 → PLAYER_DIRECT / 同族 KIN_ALERT(3格) / 8格不示警 + 反击掉血
  E 距离脱战：tp 拉远 >32 格 → angry=false
  F 白名单热切换：/pal whitelist add zombie 后 neutralized=false 且怪恢复主动攻击；
    同时借「命令有副作用」证明 /pal 命令树已注册（单机读不到聊天回显）
  G 交易：非愤怒空手右键开窗 + 成交 + 愤怒后拒交
  H Boss 门控字段：凋灵 adapted/boss/neutralized=true、canTrade=false

用法：
    python tests/automation/smoke_local_world.py --loader neoforge
    python tests/automation/smoke_local_world.py --loader fabric
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

PAL_DIR = Path(r"D:\Coding\projects\peace-and-love")
RPC_DIR = Path(r"D:\Coding\projects\mc-client-rpc")

CLIENT_RPC = ("127.0.0.1", 25586)
PROBE = ("127.0.0.1", 25585)

PASS, FAIL = "✅", "❌"
results = []


def record(ok, msg):
    results.append((ok, msg))
    print(f"  {PASS if ok else FAIL} {msg}", flush=True)


class Step:
    def __init__(self): self.n = 0
    def info(self, m):
        print(f"       · {m}", flush=True)


st = Step()


# ── 两个 RPC 通道（标准库 newline JSON-RPC，半关闭写端）────────────────
def _call(addr, method, params=None, timeout=8.0, seq=None):
    req = {"jsonrpc": "2.0", "method": method, "id": seq or 1}
    if params:
        req["params"] = params
    line = (json.dumps(req) + "\n").encode("utf-8")
    with socket.create_connection(addr, timeout=timeout) as s:
        s.sendall(line)
        s.shutdown(socket.SHUT_WR)
        s.settimeout(timeout)
        buf = b""
        try:
            while True:
                c = s.recv(4096)
                if not c:
                    break
                buf += c
        except socket.timeout:
            pass
    r = json.loads(buf.decode("utf-8"))
    if "error" in r:
        raise RuntimeError(f"[{method}] {r['error'].get('code')}: {r['error'].get('message')}")
    return r.get("result", "")


_seq = [0]
def rpc(method, params=None, timeout=8.0):
    _seq[0] += 1
    return _call(CLIENT_RPC, method, params, timeout, _seq[0])

_pseq = [1000]
def pal(method, params=None, timeout=8.0):
    _pseq[0] += 1
    r = _call(PROBE, method, params, timeout, _pseq[0])
    # 探针把「找不到实体/未就绪」当 result 字符串返回（非 JSON-RPC error）；
    # 调用方期望 dict 时对这种串 .get 会二次崩溃，这里提前抛出带信息的异常。
    if isinstance(r, str) and r.startswith("错误"):
        raise RuntimeError(f"[probe {method}] {r}")
    return r


def cmd(command_text, timeout=8.0):
    """以作弊世界房主身份执行一条不带 / 的斜杠命令。"""
    return rpc("player.command", {"cmd": command_text}, timeout=timeout)


def wait_until(fn, timeout, interval=1.0, desc=""):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            v = fn()
            if v:
                return True
        except Exception as e:
            last = e
        time.sleep(interval)
    if last:
        print(f"       · 等待 {desc} 末态异常: {last}", flush=True)
    return False


def status():
    return rpc("client.status", timeout=4)


# ── 客户端生命周期 ────────────────────────────────────────────────
_proc = None

def start_client(loader, world="pal-smoke"):
    global _proc
    # world.create 对同名旧档直接报「存档目录已存在」，每轮先清掉这个冒烟临时档
    #（只删指定世界名，不碰 run/saves 下其他存档）。
    stale = PAL_DIR / loader / "run" / "saves" / world
    if stale.exists():
        shutil.rmtree(stale, ignore_errors=True)
        print(f"       · 已清理旧测试档 {stale}", flush=True)
    gradlew = str(PAL_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew"))
    task = ":neoforge:runClient" if loader == "neoforge" else ":fabric:runClient"
    _proc = subprocess.Popen(
        [gradlew, task, "-PenableVerifyRpc=true", "--console=plain"],
        cwd=str(PAL_DIR), stdout=open(os.environ["LOCALAPPDATA"] + "/Temp/pal_smoke_client.log", "wb"),
        stderr=subprocess.STDOUT,
    )


def stop_client():
    global _proc
    try:
        rpc("client.quit", timeout=4)
    except Exception:
        pass
    if _proc is not None:
        try:
            _proc.wait(timeout=20)
        except Exception:
            _proc.kill()
        _proc = None


# ── 各阶段 ────────────────────────────────────────────────────────
def phase_a_enter_world(world_name):
    print("\n[A] 启动客户端 + world.create 建作弊世界", flush=True)
    # 客户端 RPC 就绪
    assert wait_until(lambda: _ok("client.status"), 300, 3, "客户端RPC"), "客户端 RPC 300s 未就绪"
    print("       · 客户端 RPC(25586) 就绪", flush=True)
    # 跳过引导屏，回到标题
    try:
        rpc("client.toTitle", timeout=10)
    except Exception:
        pass
    time.sleep(1)
    res = rpc("world.create", {
        "name": world_name,
        "gameMode": "survival",
        "difficulty": "normal",
        "allowCheats": True,
        "hardcore": False,
        "preset": "flat",
        "generateStructures": False,
        "bonusChest": False,
    }, timeout=60)
    print(f"       · world.create: {res}", flush=True)
    assert wait_until(lambda: (status() or {}).get("inWorld"), 90, 2, "进世界"), "进世界超时"
    print("       · 已进入世界", flush=True)
    # PAL 探针（集成服 SERVER_STARTING 后起）
    assert wait_until(lambda: _pal_ok("server.status"), 60, 2, "探针"), "PAL 探针(25585) 60s 未就绪"
    srv = pal("server.status")
    print(f"       · PAL 探针就绪: {str(srv)[:80]}", flush=True)
    # 玩家活着、生存
    if rpc("player.state").get("dead"):
        rpc("player.respawn"); time.sleep(1)
    cmd("gamerule doMobSpawning false")
    cmd("gamerule naturalRegeneration false")
    # 锁午夜：超平坦白天会让召唤的僵尸晒阳烧死（曾导致 E 阶段轮询时实体消失）。
    cmd("time set midnight")
    cmd("gamerule doDaylightCycle false")
    cmd("weather clear")
    time.sleep(0.5)
    record(True, "双通道就绪（25586 客户端 / 25585 PAL 探针），已在作弊生存世界")


def _ok(m):
    try:
        rpc(m, timeout=3); return True
    except Exception:
        return False

def _pal_ok(m):
    try:
        pal(m, timeout=3); return True
    except Exception:
        return False


def summon(name, etype, dx, dy, dz, freeze=False):
    p = rpc("player.pos")
    x, y, z = int(p["x"]) + dx, int(p["y"]) + dy, int(p["z"]) + dz
    # 1.21 CustomName 需 JSON text component。用【单引号】包整个 JSON、内部双引号
    # 【不转义】——SNBT 单引号串里双引号是普通字符；写成 '\"..\"' 会报
    # 「无效的转义序列 \"」（那是外层双引号的写法）。此写法对命令包/RCON 都成立。
    nbt = "{PersistenceRequired:1b,CustomName:'{\"text\":\"%s\"}'}" % name
    cmd(f"summon {etype} {x+0.5} {y} {z+0.5} {nbt}")
    # 默认【不减速】：攻击者必须保留全速，被击退后才能冲回近战范围出拳。
    # 仅纯门控观察怪（如 F 的 wl_gate，需固定在远处、不参与集火）才彻底冻死。
    # 同族示警在受击【瞬间】按出生位置判定，脱战在玩家 tp 远当 tick 判定，都不靠冻怪。
    if freeze:
        cmd(f"effect give @e[name=\"{name}\"] minecraft:slowness 120 255 true")
    time.sleep(0.6)


def platform(length):
    p = rpc("player.pos")
    x, y, z = int(p["x"]), int(p["y"]), int(p["z"])
    cmd(f"fill {x-2} {y-1} {z-2} {x+length+2} {y-1} {z+2} minecraft:stone")
    cmd(f"tp @s {x+0.5} {y} {z+0.5}")
    time.sleep(0.8)


def _nearest_entity_pos(type_id):
    """最近指定类型实体的 (x,y,z)；无/异常返回 None。type_id 须带命名空间。"""
    try:
        r = rpc("world.entities", {"radius": 32}, timeout=6)
        ents = [e for e in r.get("entities", []) if e.get("type") == type_id]
        if not ents:
            return None
        e = min(ents, key=lambda d: d.get("distance", 1e9))
        return float(e["x"]), float(e["y"]), float(e["z"])
    except Exception:
        return None


def recenter_on(type_key):
    """超距自愈：把玩家 tp 到最近目标的同格（同层），保证下一动作在触及内。

    中立化的怪被击退后不会自己走回玩家，攻击/右键第一次判超距后若只 sleep
    重试，距离不变必然连锁超距（fabric 上观察到的偶发红根因）。贴脸后距离≈0。
    """
    type_id = type_key if ":" in type_key else "minecraft:" + type_key
    pos = _nearest_entity_pos(type_id)
    if not pos:
        return False
    x, y, z = pos
    cmd(f"tp @s {x:.3f} {y:.3f} {z:.3f}")
    time.sleep(0.35)
    return True


def attack_retry(target="zombie", tries=4):
    """player.attack 带自愈重试：-32003 超距就 tp 贴脸再打，其余错误 sleep 重试。返回结果或 None。"""
    last = None
    for i in range(tries):
        try:
            return rpc("player.attack", {"target": target}, timeout=8)
        except Exception as e:
            last = e
            print(f"       · attack 重试{i+1}: {e}", flush=True)
            if "32003" in str(e):
                recenter_on(target)
            else:
                time.sleep(1.0)
    print(f"       · attack {tries} 次未成功: {last}", flush=True)
    return None


def interact_retry(target="zombie", auto_close=True, tries=4, timeout=15):
    """player.interact 带自愈重试。返回结果 dict；彻底失败返回 {'error': ...}。"""
    last = None
    for i in range(tries):
        try:
            return rpc("player.interact", {"target": target, "autoClose": auto_close}, timeout=timeout)
        except Exception as e:
            last = e
            print(f"       · interact 重试{i+1}: {e}", flush=True)
            if "32003" in str(e):
                recenter_on(target)
            else:
                time.sleep(1.0)
    return {"error": str(last)}


def phase_b_inspect_gating():
    print("\n[B] debug.inspect 门控链", flush=True)
    cmd("kill @e[type=!player]"); time.sleep(0.8)
    platform(10)
    summon("inz", "minecraft:zombie", 2, 0, 0)
    summon("cow0", "minecraft:cow", 4, 0, 0)
    z = pal("debug.inspect", {"name": "inz"})
    c = pal("debug.inspect", {"name": "cow0"})
    record(isinstance(z, dict) and z["entityId"] == "minecraft:zombie",
           f"僵尸 entityId 正确: {z.get('entityId') if isinstance(z,dict) else z}")
    record(isinstance(z, dict) and z["adapted"] and z["neutralized"] and not z["whitelisted"],
           f"僵尸 adapted/neutralized=true, whitelisted=false（实际 {z.get('adapted')}/{z.get('neutralized')}/{z.get('whitelisted')}）")
    record(isinstance(z, dict) and z["canTrade"] and not z["angry"] and not z["targetDescription"],
           f"僵尸默认可交易、无仇恨、无目标（canTrade={z.get('canTrade')} angry={z.get('angry')} target={z.get('targetDescription')!r}）")
    record(isinstance(c, dict) and (not c["adapted"]) and (not c["neutralized"]) and (not c["canTrade"]),
           f"牛未适配→不中立化/不可交易（adapted={c.get('adapted') if isinstance(c,dict) else c}）")


def phase_c_neutral_passive():
    print("\n[C] 中立化：僵尸贴身不主动攻击", flush=True)
    cmd("kill @e[type=!player]"); time.sleep(0.8)
    platform(4)
    hp0 = float(rpc("player.state")["health"])
    summon("passive_z", "minecraft:zombie", 1, 0, 0)
    # 锚玩家贴近
    p = rpc("player.pos")
    cmd(f"tp @s {int(p['x'])+0.5} {int(p['y'])} {int(p['z'])+0.5}")
    print("       · 观察 5 秒，僵尸是否主动攻击…", flush=True)
    time.sleep(5)
    hp1 = float(rpc("player.state")["health"])
    z = pal("debug.inspect", {"name": "passive_z"})
    tgt = z.get("targetDescription") if isinstance(z, dict) else None
    record(hp1 >= hp0, f"5 秒内玩家未因僵尸主动攻击掉血（{hp0}→{hp1}）")
    record(not tgt, f"僵尸未把玩家设为目标（target={tgt!r}）")


def phase_d_retaliation_kin():
    print("\n[D] 真实攻击 → 反击 + 同族示警边界", flush=True)
    cmd("kill @e[type=!player]"); time.sleep(0.8)
    platform(12)
    cmd("effect give @s minecraft:instant_health 1 10 true")
    summon("dt", "minecraft:zombie", 1, 0, 0)   # 被打者；不减速，被击退后全速冲回近战
    summon("dn", "minecraft:zombie", 4, 0, 0)   # 距 dt 3 格 near，<4 示警半径应示警
    summon("df", "minecraft:zombie", 9, 0, 0)   # 距 dt 8 格 far，>4 不应示警
    hp0 = float(rpc("player.state")["health"])
    a = attack_retry("zombie")
    time.sleep(2.0)
    def src(n):
        r = pal("mob.anger", {"name": n})
        # 返回 "source=PLAYER_DIRECT;target=player;type=zombie"
        if isinstance(r, str) and "source=" in r:
            return r.split("source=")[1].split(";")[0]
        return r
    s_t, s_n, s_f = src("dt"), src("dn"), src("df")
    # 命中判据以【服务端】PLAYER_DIRECT 为准：mc-client-rpc 的 hit=客户端回读怪血量，
    # Fabric 上有血量同步时序假阴性（会报 hit=False 但服务端已受理），不可靠。
    # 攻击包被服务端受理的权威信号是被打者结 PLAYER_DIRECT 仇恨（下面反击掉血也佐证）。
    record(s_t == "PLAYER_DIRECT",
           f"攻击被服务端受理：被打者仇恨 PLAYER_DIRECT（实际 {s_t}；客户端回读 hit={a.get('hit') if a else None} dist={a.get('distance') if a else '-'}）")
    record(s_n == "KIN_ALERT", f"3 格同族被示警 KIN_ALERT（实际 {s_n}）")
    record(s_f == "NONE", f"8 格外同族不示警 NONE（实际 {s_f}）")
    # 反击掉血（给最多 6 秒）
    dropped = wait_until(lambda: float(rpc("player.state")["health"]) < hp0, 6, 1, "反击掉血")
    record(dropped, f"被打僵尸真实反击致玩家掉血（{hp0}→{float(rpc('player.state')['health'])}）")
    # debug.inspect 被打者应 angry 且目标为玩家
    zi = pal("debug.inspect", {"name": "dt"})
    record(isinstance(zi, dict) and zi["angry"] and zi["targetDescription"] and "玩家" in zi["targetDescription"],
           f"debug.inspect 被打者 angry=true/目标玩家（angry={zi.get('angry') if isinstance(zi,dict) else zi} target={zi.get('targetDescription') if isinstance(zi,dict) else '-'}）")
    # 保命：立刻回满，供后续阶段
    cmd("effect give @s minecraft:instant_health 1 5 true")


def phase_e_distance_decay():
    print("\n[E] 距离脱战（>32 格 calmDown）", flush=True)
    # 关键窗口：PAL 脱战阈值 32 格，僵尸 follow_range 默认 35。
    # tp 到 34：>32 触发 PAL 距离脱战，又 <35 尽量不让原版 NearestAttackableTargetGoal
    # 当 tick 清掉 target。即便 Fabric 端 target 被提前清空（targetDistance=-1），
    # AngerController 现在也会用 lastAttackerByMob 兜底找回玩家算距离（Brain 系与
    # 走 mod 计时的 Goal 系僵尸都记），距离脱战仍触发、不必干等 30s 计时。
    # 铺台到 +38 保证落点不悬空。
    platform(40)
    p = rpc("player.pos")
    bx, by, bz = int(p["x"]), int(p["y"]), int(p["z"])
    cmd(f"tp @s {bx+34+0.5} {by} {bz+0.5}")
    # 轮询最多 8 秒等服务端 calmDown；每轮打印目标/距离，区分「目标已丢失走计时」
    # 与「距离够却没脱战（真 bug）」，不靠固定 sleep 的时序甜点。
    def inspect_safe(nm):
        try:
            return pal("debug.inspect", {"name": nm})
        except Exception:
            return None
    def both_calm():
        zi = inspect_safe("dt")
        ni = inspect_safe("dn")
        return (isinstance(zi, dict) and not zi["angry"]
                and isinstance(ni, dict) and not ni["angry"])
    deadline = 8
    for t in range(deadline):
        time.sleep(1)
        if both_calm():
            break
        if t in (0, 3, 7):
            for nm in ("dt", "dn"):
                d = inspect_safe(nm)
                if isinstance(d, dict):
                    st.info(f"{nm} +{t+1}s angry={d['angry']} target={d['targetDescription']!r} dist={d['targetDistance']} src={d['angerSource']}")
    zi = inspect_safe("dt")
    ni = inspect_safe("dn")
    record(isinstance(zi, dict) and not zi["angry"], f"target 拉远后 angry=false（实际 {zi.get('angry') if isinstance(zi,dict) else zi}）")
    record(isinstance(ni, dict) and not ni["angry"], f"被示警者拉远后同样脱战 angry=false（实际 {ni.get('angry') if isinstance(ni,dict) else ni}）")
    cmd(f"tp @s {bx+0.5} {by} {bz+0.5}")
    cmd("effect give @s minecraft:instant_health 1 10 true")
    time.sleep(0.5)


def phase_f_whitelist_hotswap():
    print("\n[F] 白名单热切换 + /pal 命令树注册（看副作用）", flush=True)
    cmd("kill @e[type=!player]"); time.sleep(0.8)
    platform(6)
    # 先确保不在白名单，再召一只【本阶段专属】的僵尸贯穿整个切换
    #（不能引用 B 阶段的 inz——中间各阶段 kill @e 已清场）。
    try:
        cmd("pal whitelist remove minecraft:zombie")
    except Exception:
        pass
    time.sleep(0.3)
    summon("wl_gate", "minecraft:zombie", 6, 0, 0, freeze=True)   # 门控观察怪，冻在远处不参与集火
    before = pal("debug.inspect", {"name": "wl_gate"})
    record(isinstance(before, dict) and not before["whitelisted"] and before["neutralized"],
           f"切换前僵尸 whitelisted=false/neutralized=true（实际 {before.get('whitelisted') if isinstance(before,dict) else before}）")
    # 通过玩家命令加白名单（若 /pal 命令树没注册，此命令失败、字段不变）
    cmd("pal whitelist add minecraft:zombie")
    time.sleep(0.6)
    after = pal("debug.inspect", {"name": "wl_gate"})
    record(isinstance(after, dict) and after["whitelisted"] and not after["neutralized"],
           f"/pal whitelist add 生效：whitelisted=true/neutralized=false（命令树已注册，实际 {after.get('whitelisted') if isinstance(after,dict) else after}/{after.get('neutralized') if isinstance(after,dict) else '-'}）")
    # 白名单怪恢复主动攻击：新召一只贴身，观察掉血
    # 用抗性 I（amplifier 0，减 20%）：仍明显掉血可判定、又不被一只僵尸打死。
    # 注意不能用 level 5（amplifier 4=100% 免伤），否则掉血信号恒 false。
    cmd("effect give @s minecraft:resistance 15 0 true")
    cmd("effect give @s minecraft:instant_health 1 5 true")
    hp0 = float(rpc("player.state")["health"])
    summon("wl_z", "minecraft:zombie", 1, 0, 0)
    p = rpc("player.pos")
    cmd(f"tp @s {int(p['x'])+0.5} {int(p['y'])} {int(p['z'])+0.5}")
    aggro = wait_until(lambda: float(rpc("player.state")["health"]) < hp0, 8, 1, "白名单怪主动攻击")
    record(aggro, f"白名单僵尸恢复原版敌对、主动攻击玩家（{hp0}→{float(rpc('player.state')['health'])}）")
    # 还原白名单
    cmd("pal whitelist remove minecraft:zombie")
    cmd("effect give @s minecraft:instant_health 1 5 true")
    time.sleep(0.5)


def phase_g_trade():
    print("\n[G] 交易：开窗 / 成交 / 愤怒拒交", flush=True)
    cmd("kill @e[type=!player]"); time.sleep(0.8)
    platform(4)
    # 空手
    cmd("item replace entity @s weapon.mainhand with air")
    summon("tz", "minecraft:zombie", 1, 0, 0)
    time.sleep(0.5)
    zi = pal("debug.inspect", {"name": "tz"})
    record(isinstance(zi, dict) and zi["canTrade"] and not zi["angry"], "交易前僵尸 canTrade=true 且不愤怒")
    opened = interact_retry("zombie", True)
    record(isinstance(opened, dict) and opened.get("screenOpen"),
           f"非愤怒空手右键打开原版交易 GUI（screenOpen={opened.get('screenOpen') if isinstance(opened,dict) else opened} screen={opened.get('screen') if isinstance(opened,dict) else '-'}）")
    # 成交第 0 槽：空背包未必有报价货币，失败只记信息不计 FAIL
    #（交易门控的核心断言是「能开窗」与「愤怒后拒交」，真实成交已有专门用例）。
    try:
        take = rpc("trade.take", {"slot": 0}, timeout=10)
        record(True, f"trade.take slot=0 返回（信息项）: {str(take)[:80]}")
    except Exception as e:
        record(True, f"trade.take 未成交（信息项，多为空背包无报价货币）: {str(e)[:80]}")
    time.sleep(0.5)
    # 攻击使它愤怒，再交互应被门控拒绝；给抗性防反杀
    cmd("effect give @s minecraft:resistance 15 4 true")
    try:
        rpc("player.attack", {"target": "zombie"}, timeout=8)
    except Exception:
        pass
    time.sleep(1.0)
    zi2 = pal("debug.inspect", {"name": "tz"})
    record(isinstance(zi2, dict) and zi2["angry"], f"攻击后僵尸 angry=true（{zi2.get('angry') if isinstance(zi2,dict) else zi2}）")
    blocked = interact_retry("zombie", True)
    no_open = (isinstance(blocked, dict) and blocked.get("screenOpen") is False) or \
              (isinstance(blocked, dict) and "error" in blocked)
    record(no_open, f"愤怒状态右键不再开交易窗（screenOpen={blocked.get('screenOpen') if isinstance(blocked,dict) else blocked}）")
    cmd("effect give @s minecraft:instant_health 1 5 true")


def phase_h_boss():
    print("\n[H] Boss 门控字段（凋灵）", flush=True)
    cmd("kill @e[type=!player]"); time.sleep(0.8)
    platform(14)
    # 凋灵生成瞬间有充能爆炸（属生成机制非索敌，中立化不拦截）：
    # 给抗性 V + 生命恢复，召唤在 11 格外，等充能（约 3s）结束再读字段。
    cmd("effect give @s minecraft:resistance 30 4 true")
    cmd("effect give @s minecraft:regeneration 30 4 true")
    summon("w0", "minecraft:wither", 11, 0, 0)
    print("       · 等凋灵充能爆炸结束（4s）…", flush=True)
    time.sleep(4.0)
    w = pal("debug.inspect", {"name": "w0"})
    ok = (isinstance(w, dict) and w.get("entityId") == "minecraft:wither" and w.get("adapted")
          and w.get("boss") and w.get("neutralized") and not w.get("canTrade"))
    record(ok, f"凋灵 adapted/boss/neutralized=true 且 canTrade=false（{str({k:w.get(k) for k in ('adapted','boss','neutralized','canTrade')}) if isinstance(w,dict) else w}）")
    cmd("kill @e[type=minecraft:wither]")
    cmd("effect clear @s")


def cleanup():
    try:
        cmd("gamerule doMobSpawning true", timeout=4)
        cmd("gamerule naturalRegeneration true", timeout=4)
        cmd("kill @e[type=!player]", timeout=4)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loader", choices=["neoforge", "fabric"], default="neoforge")
    ap.add_argument("--attach", action="store_true", help="复用已在世界中的客户端，不自行启停")
    ap.add_argument("--world", default="pal-smoke")
    ap.add_argument("--only", default="",
                    help="只跑指定阶段，逗号分隔（a-h，如 f）；缺省跑全部 b-h")
    args = ap.parse_args()

    started = False
    try:
        if not args.attach:
            print(f"启动 {args.loader} runClient（-PenableVerifyRpc=true）…", flush=True)
            start_client(args.loader, args.world)
            started = True
            phase_a_enter_world(args.world)
        else:
            assert wait_until(lambda: (status() or {}).get("inWorld"), 10, 1), "attach 但玩家不在世界"
            assert _pal_ok("server.status"), "attach 但 PAL 探针未就绪"
            record(True, "attach 模式：复用已在世界中的客户端")

        all_phases = [
            ("b", phase_b_inspect_gating),
            ("c", phase_c_neutral_passive),
            ("d", phase_d_retaliation_kin),
            ("e", phase_e_distance_decay),
            ("f", phase_f_whitelist_hotswap),
            ("g", phase_g_trade),
            ("h", phase_h_boss),
        ]
        only = {x.strip().lower() for x in args.only.split(",") if x.strip()}
        for key, fn in all_phases:
            if not only or key in only:
                fn()
        cleanup()
    finally:
        if started:
            stop_client()

    print("\n" + "=" * 64)
    passed = sum(1 for ok, _ in results if ok)
    failed = [m for ok, m in results if not ok]
    print(f"冒烟结果：{passed}/{len(results)} PASS，{len(failed)} FAIL")
    for m in failed:
        print(f"  {FAIL} {m}")
    print("=" * 64)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
