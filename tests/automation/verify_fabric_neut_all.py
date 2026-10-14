#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-NEUT-005/006/007 Fabric 端真机回归。

复用 NeoForge 同一套 verify_* 脚本（业务逻辑零改动），只在加载后注入 Fabric 服
的三条通道：
  - 客户端 RPC 25586（fabric 版 mc-client-rpc 客户端，已连 25566）—— 无需改
  - RCON 25575 -> 25576（combat_loop_test.SERVER_RCON_PORT，server_rcon 内部读模块全局）
  - PAL 探针 25585 -> 25587（各脚本模块级 PAL_RPC）
  - CFG 白名单配置路径 -> ~/minecraft-fabric/config/peaceandlove.json
"""
import importlib.util
import os
import sys
import traceback

AUTO = r"D:\Coding\projects\peace-and-love\tests\automation"
sys.path.insert(0, r"D:\Coding\projects\mc-client-rpc\scripts")
sys.path.insert(0, AUTO)

import combat_loop_test  # noqa: E402
combat_loop_test.SERVER_RCON_PORT = 25576

FABRIC_CFG = "/home/mc/minecraft-fabric/config/peaceandlove.json"
FABRIC_PROBE = ("192.0.2.10", 25587)

SCRIPTS = [
    "verify_neut005_phantom.py",      # 幻翼：不俯冲 + 反击
    "verify_neut006_wither.py",       # 凋灵：placeBlock 图案召唤 + 侧头拦 + 主头反击
    "verify_neut007_piglin.py",       # 僵尸猪灵：4 格单层 KinAlerter
    "verify_neut007_enderman.py",     # 末影人：凝视不激怒 + 反击
    "verify_neut006_warden.py",       # 监守者：自然召唤 + BrainAttackGate + 反击
    "verify_neut005_regression.py",   # 6 种回归
]

results = []
only = set(sys.argv[1:])
run_list = [s for s in SCRIPTS if not only or s in only]
for name in run_list:
    path = os.path.join(AUTO, name)
    modname = name[:-3]
    print("\n" + "=" * 70, flush=True)
    print(f"### Fabric 回归：{name}", flush=True)
    print("=" * 70, flush=True)
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    # 注入 Fabric 通道
    mod.PAL_RPC = FABRIC_PROBE
    if hasattr(mod, "CFG"):
        mod.CFG = FABRIC_CFG
    try:
        rc = mod.main()
        code = rc if isinstance(rc, int) else 0
        ok = (code == 0)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        ok = (code == 0)
    except Exception:
        traceback.print_exc()
        code, ok = 1, False
    results.append((name, ok))
    print(f">>> {name} => {'PASS' if ok else 'FAIL'} (exit={code})", flush=True)

print("\n" + "#" * 70, flush=True)
print("# Fabric 回归汇总", flush=True)
for name, ok in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}", flush=True)
passed = sum(1 for _, ok in results if ok)
print(f"# {passed}/{len(results)} 通过", flush=True)
sys.exit(0 if passed == len(results) else 1)
