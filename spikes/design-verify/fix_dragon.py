"""
修正末影龙的白名单标记
=========================
末影龙 v1.0 不适配、不进默认白名单（用户决策），
但 neutralization_plan_v3.json 里仍标着 default_whitelisted: true。
"""
import json
from pathlib import Path

R3 = Path(__file__).resolve().parent.parent / "r3-ai" / "neutralization_plan_v3.json"
d = json.loads(R3.read_text(encoding="utf-8"))

for m in d["goal_system"] + d["brain_system"]:
    if m["id"] == "ender_dragon":
        m["default_whitelisted"] = False
        m["adapted_v1"] = False
        m["ai_system"] = "custom (EnderDragonPhaseManager)"
        m["note"] = ("v1.0 暂缓：自有 Phase AI，不适配也不进默认白名单 → "
                     "行为完全不变；配置无效时日志给 INFO 提示")

d["correction_3"] = "末影龙不适配、不进默认白名单（行为完全不变）"
R3.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

wl = [m["id"] for m in d["goal_system"] + d["brain_system"]
      if m.get("default_whitelisted")]
print(f"默认白名单最终 {len(wl)} 项：{sorted(wl)}")

adapted = [m["id"] for m in d["goal_system"] + d["brain_system"]
           if m.get("adapted_v1") is not False and m["id"] != "ender_dragon"]
print(f"v1.0 已适配 {len(adapted)} 项")
print("\n✅ 完成")
