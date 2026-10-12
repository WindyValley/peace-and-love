#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-TRADE-003 真机验证：右键中立怪物打开原版交易 GUI 的门控真值表。

前置：客户端已启动并连上测试服（另跑 launch_and_connect.py）。
被测：部署在 192.0.2.10 的最新 PAL jar；驱动 mod mc-client-rpc 带 player.interact。

用例（每例独立隔间 + 命名 NoAI 定点怪，几何固定、互不干扰）：
  1. 空手右键中立僵尸          → 开 MerchantScreen，offerCount>0
  2. 僵尸加入白名单            → 不开
  3. trading_enabled=false     → 不开（改远端配置 + pal reload，finally 还原）
  4. 监守者 + boss 开关关(默认) → 不开
  5. 监守者 + boss 开关开       → 开（Boss 正向，证明只被 boss 门控拦住）
  6. 玩家先攻击僵尸（PLAYER_DIRECT）→ 仇恨中右键不开
  7. 主手持物右键僵尸          → 不开（保留原版交互）
  8. 未适配生物（牛）          → 不开（保持原版）

判定信号：客户端 player.interact 返回的 screenOpen（5 tick 后读 mc.screen
是否 MerchantScreen，服务端权威开屏包驱动）+ offerCount；配置类用例另读远端
JSON 确认开关真的改到了文件。退出码 0=全绿。
"""
import json
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
from combat_loop_test import rpc, server_rcon  # noqa: E402

SSH_TARGET = "mc@192.0.2.10"
REMOTE_DIR = "/home/mc/minecraft"
CFG = f"{REMOTE_DIR}/config/peaceandlove.json"
PAL_RPC = ("192.0.2.10", 25585)
_id = [100]

results = []


def log(*a):
    print(*a, flush=True)


def ssh_run(cmd, timeout=30):
    r = subprocess.run(["ssh", SSH_TARGET, cmd],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.returncode


def set_remote_flag(key, value):
    """改远端配置 JSON 的布尔字段（不经过 RCON，避免冒号转义），随后 pal reload。"""
    py = (f"import json;p='{CFG}';"
          f"d=json.load(open(p));d['{key}']={True if value else False};"
          f"json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)")
    out, rc = ssh_run(f"python3 -c \"{py}\"")
    if rc != 0:
        raise RuntimeError(f"改远端配置失败: {out}")
    server_rcon("pal reload")
    time.sleep(1.0)


def remote_flag(key):
    out, _ = ssh_run(
        f"python3 -c \"import json;print(json.load(open('{CFG}'))['{key}'])\"")
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


def arena(ix, iy, iz):
    server_rcon(f"fill {ix-1} {iy-1} {iz-1} {ix+2} {iy-1} {iz+1} stone")
    server_rcon(f"fill {ix-1} {iy} {iz-1} {ix+2} {iy+2} {iz+1} stone")
    server_rcon(f"fill {ix} {iy} {iz} {ix+1} {iy+1} {iz} air")


def clear_hand():
    # 注意：「item replace … []」实测无效（回显成功但不清槽）；必须用 with air。
    server_rcon("item replace entity Dev weapon.mainhand with air")
    server_rcon("item replace entity Dev weapon.offhand with air")


def summon(ix, iy, iz, etype, name):
    server_rcon(f"summon {etype} {ix+1} {iy} {iz} "
                f"{{CustomName:'{{\"text\":\"{name}\"}}',PersistenceRequired:1b,NoAI:1b}}")
    time.sleep(0.8)


def interact(etype):
    """对最近该类实体右键；busy 退避重试。返回结构化 dict。"""
    last = None
    for _ in range(3):
        try:
            return rpc("player.interact", {"target": etype, "autoClose": True}, timeout=15)
        except RuntimeError as e:
            last = e
            if "[-32002]" in str(e):
                raise
            time.sleep(1.0)
    raise RuntimeError(f"interact 持续失败: {last}")


def case(num, label, etype, name, expect_open, ix, prepare=None):
    log(f"\n--- 用例 {num}：{label} ---")
    server_rcon(f"kill @e[name={name}]")
    arena(ix, iy, iz)
    server_rcon(f"tp Dev {ix+0.5} {iy} {iz+0.5}")
    time.sleep(0.4)
    if prepare:
        prepare()
    time.sleep(0.3)
    summon(ix, iy, iz, etype, name)
    try:
        r = interact(etype)
        opened = bool(r.get("screenOpen"))
        offers = r.get("offerCount")
        log(f"  返回: {r}")
        ok = (opened == expect_open)
        if expect_open:
            ok = ok and isinstance(offers, int) and offers > 0
            log(f"  开界面={opened} 报价条数={offers}（期望开且>0）")
        else:
            log(f"  开界面={opened} screenClass={r.get('screenClass')}（期望不开）")
        results.append((label, ok))
        return r
    finally:
        server_rcon(f"kill @e[name={name}]")
        server_rcon(f"fill {ix-1} {iy} {iz-1} {ix+2} {iy+2} {iz+1} air")


iy, iz = -57, 23


def natural_warden_cases():
    """用例 4/5：尖啸体自然召唤监守者（/summon 会 5 秒钻地自灭，NoAI 也挡不住）。

    铺 9x9 露天围栏 → 中央放 sculk_shrieker[can_summon=true] →
    玩家在 8 格内真实走动(STEP)攒 4 次警告（约 30-40s）→ 监守者钻出。
    钻出结束后一只怪复用两例：boss 关→不开；boss 开→开。
    几何只 tp 玩家，绝不 tp 监守者（钻出期 tp 会让服务端实体消失）。
    """
    import re as _re
    ix, cx, cz = 82, 86, 27          # 围栏 x∈[81,89]，中央尖啸体 (86,*-58*,27)
    floor_y, feet_y = iy - 1, iy

    def warden_present():
        out = server_rcon("execute if entity @e[type=warden]")
        return "passed" in out.lower() or "成功" in out

    def warden_pos():
        out = server_rcon("data get entity @e[type=warden,limit=1] Pos")
        m = _re.findall(r"[-+]?\d+\.\d+", out)
        return tuple(float(v) for v in m[:3]) if len(m) >= 3 else None

    def emerging():
        out = server_rcon("data get entity @e[type=warden,limit=1] Brain")
        return "is_emerging" in out

    def adjacent_interact():
        pos = warden_pos()
        if not pos:
            return None
        wx, wy, wz = pos
        # 站监守者南侧 2 格、同一地板高度；yaw=180 朝北面向它
        server_rcon(f"tp Dev {wx} {wy} {wz+2.0} 180 0")
        time.sleep(0.4)
        return interact("warden")

    log("\n--- 用例 4/5 准备：尖啸体自然召唤监守者 ---")
    server_rcon("kill @e[type=warden]")
    # 沿 z 轴 13 格平整直道（实测：必须有真实位移 STEP；画圈贴墙原地踏步无振动）。
    server_rcon(f"fill {cx-1} {floor_y} {cz-6} {cx+1} {floor_y} {cz+6} deepslate")
    server_rcon(f"fill {cx-1} {feet_y} {cz-6} {cx+1} {feet_y+2} {cz+6} air")
    server_rcon(f"setblock {cx} {floor_y} {cz} minecraft:sculk_shrieker[can_summon=true]")
    # can_summon 是方块状态，data get block 只给 block-entity NBT 不含它；
    # 必须用 execute if block 按 blockstate 判定（NBT 写法 {can_summon:1b} 会被静默忽略）。
    bs = server_rcon(
        f"execute if block {cx} {floor_y} {cz} minecraft:sculk_shrieker[can_summon=true]")
    log("  can_summon blockstate 判定:", bs.strip())
    if "passed" not in bs.lower() and "成功" not in bs:
        results.append(("监守者尖啸体 can_summon 放置", False))
        return

    # 起点尖啸体南侧 5 格，持续按 W，到南北边界掉头，直线反复穿过尖啸体。
    server_rcon(f"tp Dev {cx+0.5} {feet_y} {cz+5.5} 180 0")
    time.sleep(0.6)
    rpc("player.move", {"forward": 1}, timeout=5)
    summoned = False
    deadline = time.time() + 110        # 实测 4 警告约 38s，留足余量
    facing_north = True
    last_turn = 0.0
    while time.time() < deadline:
        pos = rpc("player.pos", timeout=5)
        dz = pos.get("z", cz) - cz
        now = time.time()
        if now - last_turn > 1.0 and (dz <= -4.0 or dz >= 4.5):
            facing_north = not facing_north
            yaw = 180 if facing_north else 0
            ztp = cz + (-4.0 if dz <= 0 else 4.5)
            rpc("player.look", {"yaw": yaw, "pitch": 0}, timeout=5)
            server_rcon(f"tp Dev {pos.get('x')} {feet_y} {ztp} {yaw} 0")
            last_turn = now
        if warden_present():
            summoned = True
            break
        time.sleep(0.5)
    rpc("player.stop", timeout=5)
    if not summoned:
        results.append(("尖啸体自然召唤监守者(110s 内)", False))
        log("  !! 110s 内未召唤出监守者")
        server_rcon(f"fill {cx-1} {floor_y} {cz-6} {cx+1} {feet_y+2} {cz+6} air")
        return
    log("  监守者已召唤，等钻出结束（is_emerging 消失，最多 15s）...")
    ok_emerge = False
    t0 = time.time()
    while time.time() - t0 < 15:
        if not emerging():
            ok_emerge = True
            break
        time.sleep(1.0)
    log(f"  钻出结束={ok_emerge}（is_emerging 已消失）")
    time.sleep(0.5)

    # 用例 4：boss 开关默认关 → 不开
    log("\n--- 用例 4：监守者 + boss_trading_enabled=false → 不开 ---")
    log(f"  远端 boss_trading_enabled={remote_flag('boss_trading_enabled')}（应 False）")
    r4 = adjacent_interact()
    if r4 is None:
        results.append(("监守者+boss关→不开", False))
    else:
        opened = bool(r4.get("screenOpen"))
        log(f"  返回: {r4}")
        results.append(("监守者+boss关→不开", not opened))

    # 用例 5：boss 开关开 → 开（同一只监守者）
    log("\n--- 用例 5：监守者 + boss_trading_enabled=true → 开 ---")
    set_remote_flag("boss_trading_enabled", True)
    log(f"  远端 boss_trading_enabled={remote_flag('boss_trading_enabled')}（应 True）")
    r5 = adjacent_interact()
    if r5 is None:
        results.append(("监守者+boss开→开", False))
    else:
        opened = bool(r5.get("screenOpen"))
        offers = r5.get("offerCount")
        log(f"  返回: {r5}")
        results.append(("监守者+boss开→开", opened and isinstance(offers, int) and offers > 0))

    # 撤离玩家再拆直道，最后杀监守者
    server_rcon("tp Dev 40.5 -57 23.5")
    time.sleep(0.3)
    server_rcon("kill @e[type=warden]")
    server_rcon(f"fill {cx-1} {floor_y} {cz-6} {cx+1} {feet_y+2} {cz+6} air")
    set_remote_flag("boss_trading_enabled", False)


def main():
    st = rpc("client.status")
    log("客户端状态:", st)
    if not (isinstance(st, dict) and st.get("inWorld")):
        sys.exit("客户端未进世界，先跑 launch_and_connect.py")

    if rpc("player.state")["dead"]:
        rpc("player.respawn")
        time.sleep(2)
    server_rcon("gamerule doMobSpawning false")
    server_rcon("effect give Dev resistance 600 1 true")
    clear_hand()

    # 起始干净前提
    server_rcon("pal whitelist remove zombie")
    set_remote_flag("trading_enabled", True)
    set_remote_flag("boss_trading_enabled", False)
    time.sleep(0.5)

    try:
        # 1. 空手右键中立僵尸 → 开
        r1 = case(1, "空手右键中立僵尸→开交易界面", "zombie", "ttest", True, 46)

        # 2. 白名单内含僵尸 → 不开（改完对新召唤实体生效）
        def wl_add():
            server_rcon("pal whitelist add zombie")
            time.sleep(0.5)
        case(2, "僵尸在白名单→不开", "zombie", "ttest", False, 50, wl_add)
        server_rcon("pal whitelist remove zombie")

        # 3. 全局交易开关关 → 不开
        def trade_off():
            set_remote_flag("trading_enabled", False)
            log(f"  远端 trading_enabled={remote_flag('trading_enabled')}（应 False）")
        case(3, "trading_enabled=false→不开", "zombie", "ttest", False, 54, trade_off)
        set_remote_flag("trading_enabled", True)

        # 4/5. 监守者 Boss 门控（自然召唤，专用流程）
        natural_warden_cases()

        # 6. 仇恨中 → 不开（NoAI 僵尸被打不还手，但 PLAYER_DIRECT 已记录）
        log("\n--- 用例 6：攻击后仇恨中右键不开 ---")
        name = "atest"
        ix = 66
        server_rcon(f"kill @e[name={name}]")
        arena(ix, iy, iz)
        server_rcon(f"tp Dev {ix+0.5} {iy} {iz+0.5}")
        time.sleep(0.4)
        summon(ix, iy, iz, "zombie", name)
        try:
            atk = None
            for _ in range(3):
                try:
                    atk = rpc("player.attackNearest", {"target": "zombie"}, timeout=20)
                    break
                except RuntimeError as e:
                    log("  攻击重试:", e)
                    time.sleep(1.0)
            time.sleep(0.6)
            src = anger_source(name)
            r6 = interact("zombie")
            opened = bool(r6.get("screenOpen"))
            log(f"  攻击: {atk}")
            log(f"  anger source={src}（应 PLAYER_DIRECT）；右键 screenOpen={opened}（应 False）")
            ok6 = (src == "PLAYER_DIRECT" and not opened)
            results.append(("攻击后仇恨中→不开", ok6))
        finally:
            server_rcon(f"kill @e[name={name}]")
            server_rcon(f"fill {ix-1} {iy} {iz-1} {ix+2} {iy+2} {iz+1} air")

        # 7. 主手持物 → 不开
        def hold_item():
            server_rcon("item replace entity Dev weapon.mainhand with stone")
        case(7, "主手持物右键→不开(保留原版)", "zombie", "ttest", False, 70, hold_item)
        clear_hand()

        # 8. 未适配生物（牛）→ 不开
        case(8, "未适配生物牛→不开(保持原版)", "cow", "ctest", False, 74)

    finally:
        # 还原全部临时改动
        try:
            clear_hand()
            server_rcon("pal whitelist remove zombie")
            set_remote_flag("trading_enabled", True)
            set_remote_flag("boss_trading_enabled", False)
            server_rcon("kill @e[name=ttest]")
            server_rcon("kill @e[name=wtest]")
            server_rcon("kill @e[name=atest]")
            server_rcon("kill @e[name=ctest]")
            server_rcon("gamerule doMobSpawning true")
            server_rcon("tp Dev 40.5 -57 23.5")
        except Exception as e:
            log("清理异常:", e)

    log("\n" + "=" * 56)
    allok = True
    for label, ok in results:
        log(f"{'PASS' if ok else 'FAIL'}  {label}")
        allok = allok and ok
    log("=" * 56)
    log("全部通过" if allok else "有用例失败")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
