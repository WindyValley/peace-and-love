#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 Fabric 服（192.0.2.10:25566 / RCON 25576）上跑全套交易真机回归。

不修改仓库里的 verify 脚本：跑前 monkeypatch combat_loop_test.SERVER_RCON_PORT
到 Fabric 服的 25576，双槽脚本的远端配置路径指到 minecraft-fabric。客户端 RPC 25586
与平台无关（fabric 版 mc-client-rpc 监听同一端口）。

依次跑：单次成交 → 补货后再购 → 原生商人零回归 → 双槽支付。
"""
import importlib.util, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

RPC_SCRIPTS = r"D:\Coding\projects\mc-client-rpc\scripts"
TEST_DIR = r"D:\Coding\projects\peace-and-love\tests\automation"
sys.path.insert(0, RPC_SCRIPTS)
sys.path.insert(0, TEST_DIR)

import combat_loop_test  # noqa: E402
combat_loop_test.SERVER_RCON_PORT = 25576   # Fabric 服独立 RCON
print("RCON ->", combat_loop_test.SERVER_HOST, combat_loop_test.SERVER_RCON_PORT)

FABRIC_CFG = "/home/mc/minecraft-fabric/config/peaceandlove.json"

def load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TEST_DIR, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

jobs = [
    ("单次成交 purchase", "verify_trade_purchase.py", {}),
    ("补货后再购 restock_repurchase", "verify_trade_restock_repurchase.py", {}),
    ("原生商人零回归 native", "verify_native_merchant_regression.py", {}),
    ("双槽支付 dual", "verify_dual_slot_payment.py", {"CFG": FABRIC_CFG}),
]

summary = []
for title, fname, patch_attrs in jobs:
    print("\n" + "#"*70)
    print(f"# FABRIC: {title}")
    print("#"*70, flush=True)
    modname = "vf_" + fname.replace(".py", "")
    try:
        m = load(modname, fname)
        for k, v in patch_attrs.items():
            setattr(m, k, v)
        m.main()
        summary.append((title, "PASS"))
    except SystemExit as e:
        summary.append((title, "PASS" if str(e.code) in ("0", "None") else f"FAIL(exit {e.code})"))
    except Exception as e:
        summary.append((title, f"FAIL: {type(e).__name__}: {e}"))

print("\n" + "="*70)
print("FABRIC 真机汇总")
print("="*70)
bad = 0
for title, r in summary:
    print(f"{r:16} {title}")
    if r != "PASS": bad += 1
print("="*70)
print("全部通过" if bad == 0 else f"{bad}/{len(summary)} 组失败")
sys.exit(1 if bad else 0)
