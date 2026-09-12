"""核对 neutralization_plan_v3.json 的实际构成，找出 33 vs 32 的差异"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
d = json.loads((ROOT / "spikes/r3-ai/neutralization_plan_v3.json").read_text(encoding="utf-8"))

goal = d["goal_system"]
brain = d["brain_system"]

print("=== goal_system 全部 %d 项 ===" % len(goal))
for i, e in enumerate(goal, 1):
    flag = " [白名单]" if e.get("default_whitelisted") else ""
    print("%2d. %-20s %s%s" % (i, e["id"], e["zh"], flag))

print("\n=== brain_system 全部 %d 项 ===" % len(brain))
for i, e in enumerate(brain, 1):
    flag = " [白名单]" if e.get("default_whitelisted") else ""
    print("%2d. %-20s %s%s" % (i, e["id"], e["zh"], flag))

print("\n=== 白名单项汇总 ===")
wl = [e["id"] for e in goal + brain if e.get("default_whitelisted")]
print("goal+brain 中标记为白名单的:", wl, "共", len(wl), "项")

# 设计文档说白名单 6 项：pillager/vindicator/evoker/vex/phantom/shulker
EXPECTED_WL = {"pillager", "vindicator", "evoker", "vex", "phantom", "shulker"}
print("设计预期白名单:", sorted(EXPECTED_WL))
print("JSON 白名单与预期差集:", set(wl) - EXPECTED_WL)
print("预期但 JSON 未标:", EXPECTED_WL - set(wl))

# 末影龙检查
all_ids = [e["id"] for e in goal + brain]
print("\n末影龙在列表中?", "ender_dragon" in all_ids)
