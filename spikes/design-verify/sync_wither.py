"""
同步凋灵决策到 spike 产物 JSON
=================================
用户 2026-09-11 决策：凋灵移出默认白名单，默认中立化。
更新 neutralization_plan_v3.json 与 adapted_mobs_v1.json。
"""
import json
from pathlib import Path

R3 = Path(__file__).resolve().parent.parent / "r3-ai" / "neutralization_plan_v3.json"
DV = Path(__file__).resolve().parent / "adapted_mobs_v1.json"

# ── 1. neutralization_plan_v3.json ──
d = json.loads(R3.read_text(encoding="utf-8"))
changed = []
for m in d["goal_system"]:
    if m["id"] == "wither" and m.get("default_whitelisted"):
        m["default_whitelisted"] = False
        m["note"] = ("用户 2026-09-11 决策：移出默认白名单，默认中立化"
                     "（boss_trading_enabled=false 时不开交易）")
        changed.append("wither")
d["correction_2"] = "凋灵移出默认白名单（用户 2026-09-11）；默认白名单最终为 6 项"
R3.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

wl = [m["id"] for m in d["goal_system"] + d["brain_system"]
      if m.get("default_whitelisted")]
print(f"[1] {R3.name}")
print(f"    修改：{changed}")
print(f"    默认白名单 {len(wl)} 项：{wl}")

# ── 2. adapted_mobs_v1.json ──
if DV.exists():
    a = json.loads(DV.read_text(encoding="utf-8"))
    before = list(a.get("default_whitelist", []))
    a["default_whitelist"] = [x for x in before if x != "wither"]
    a["decision_log"] = a.get("decision_log", [])
    a["decision_log"].append(
        "2026-09-11 凋灵(wither)移出默认白名单，默认中立化")
    DV.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[2] {DV.name}")
    print(f"    白名单 {len(before)} → {len(a['default_whitelist'])} 项")
    print(f"    {a['default_whitelist']}")

print("\n✅ 同步完成")
