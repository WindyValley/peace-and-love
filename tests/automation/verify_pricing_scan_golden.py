#!/usr/bin/env python3
"""T-PRICE-001 真机黄金回归。

前置：
  1. 专用服务器 192.0.2.10 已部署「带 verify RPC」的最新 peace-and-love jar
     （构建开关 -PenableVerifyRpc=true），并已重启完成数据包加载；
  2. 本脚本只走服务端探针 25585（pricing.scan），不需要客户端/玩家在线。

流程：
  连 25585 调 pricing.scan 拿运行时表扫描结果（rows: entity/item/epk/count_max），
  与 spikes/design-verify/final_pricing_128.json 中属于 38 适配生物的 70 条逐条比对，
  报告条数、epk 误差、countMax 误差、缺失/多余、保守估计条目、耗时、告警。
"""
import json
import socket
import sys
from pathlib import Path

PAL_RPC = ("192.0.2.10", 25585)
ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "spikes" / "design-verify" / "final_pricing_128.json"
OUT = ROOT / "build" / "pricing_scan_real.json"

ADAPTED = [
    "zombie", "zombie_villager", "husk", "drowned", "zombified_piglin",
    "skeleton", "wither_skeleton", "stray", "bogged", "giant",
    "spider", "cave_spider", "creeper", "ghast", "blaze", "witch",
    "slime", "magma_cube", "enderman", "endermite", "guardian",
    "elder_guardian", "illusioner", "ravager", "silverfish", "shulker",
    "phantom", "pillager", "vindicator", "evoker", "vex", "wither",
    "piglin", "piglin_brute", "hoglin", "zoglin", "warden", "breeze",
]
EPK_TOL = 1e-9


def pal_rpc(method, params=None, timeout=30):
    req = json.dumps({"jsonrpc": "2.0", "method": method,
                      "params": params or {}, "id": 1})
    with socket.create_connection(PAL_RPC, timeout=timeout) as s:
        s.sendall((req + "\n").encode())
        buf = b""
        s.settimeout(timeout)
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    resp = json.loads(buf.decode())
    if "error" in resp:
        raise RuntimeError(f"RPC 错误: {resp['error']}")
    return resp["result"]


def main():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    g = {}
    for e in golden["entries"]:
        if e["entity"] in ADAPTED:
            g.setdefault((e["entity"], e["item"]), []).append(
                (e["epk"], e["count_max"]))

    print(f"调用 {PAL_RPC} pricing.scan ...")
    res = pal_rpc("pricing.scan")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"扫描 {res['scanned']} 生物 → {res['entries']} 条，"
          f"耗时 {res['elapsed_ms']} ms，告警 {len(res['warnings'])} 条；已存 {OUT.name}")

    actual = {}
    for r in res["rows"]:
        actual.setdefault((r["entity"], r["item"]), []).append(
            (r["epk"], r["count_max"], r.get("approximated", False)))

    missing, extra, epk_bad, cnt_bad, n_bad = [], [], [], [], []
    for key, exp in g.items():
        act = actual.get(key)
        if act is None:
            missing.append(key); continue
        if len(act) != len(exp):
            n_bad.append((key, len(exp), len(act))); continue
        for (e_epk, e_cnt), (a_epk, a_cnt, _) in zip(exp, act):
            if abs(e_epk - a_epk) > EPK_TOL:
                epk_bad.append((key, e_epk, a_epk))
            if e_cnt != a_cnt:
                cnt_bad.append((key, e_cnt, a_cnt))
    for key in actual:
        if key not in g:
            extra.append(key)

    approx = [f"{r['entity']}/{r['item']}" for r in res["rows"]
              if r.get("approximated")]

    print("\n" + "=" * 70)
    print(f"黄金适配子集 {sum(len(v) for v in g.values())} 条 / "
          f"真机 {res['entries']} 条 / (entity,item) 种类 {len(g)} vs {len(actual)}")
    print("=" * 70)
    for name, bad in [("缺失", missing), ("多余", extra),
                      ("条数不一致", n_bad), ("epk 不一致", epk_bad),
                      ("countMax 不一致", cnt_bad)]:
        print(f"{name}: {len(bad)}")
        for x in bad[:15]:
            print("   ", x)

    print(f"\n保守估计(0.3)条目 {len(approx)}:")
    for x in approx:
        print("   ", x)
    if res["warnings"]:
        print(f"\n扫描告警 {len(res['warnings'])}（前 10）:")
        for w in res["warnings"][:10]:
            print("   ", w)

    ok = not (missing or extra or n_bad or epk_bad or cnt_bad)
    print("\n" + ("✅ 真机黄金回归全部通过：epk/countMax 与基线逐条一致"
                  if ok else "❌ 存在差异，见上"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
