"""
产出 v1.0 已适配生物清单 —— 供 design 文档与 dev 阶段代码常量使用
====================================================================
数据源：spikes/r3-ai/neutralization_plan_v3.json
注意：goal_system 有 33 项，需排除末影龙（自有 AI，v1.0 暂缓）后为 32。
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE.parent / "r3-ai" / "neutralization_plan_v3.json"
data = json.loads(SRC.read_text(encoding="utf-8"))

goal = data["goal_system"]
brain = data["brain_system"]
special = data["special_adaptations"]

print("=" * 78)
print("v1.0 已适配生物清单")
print("=" * 78)

# 找出 goal_system 中的异常项（末影龙应属自有 AI）
DEFER = {"ender_dragon"}
goal_v1 = [m for m in goal if m["id"] not in DEFER]
deferred = [m for m in goal if m["id"] in DEFER]

print(f"\ngoal_system 原始 {len(goal)} 项")
if deferred:
    print(f"  排除（v1.0 暂缓）：{[m['id'] for m in deferred]}")
print(f"  → Goal 系 v1.0：{len(goal_v1)} 项")
print(f"brain_system：{len(brain)} 项")
print(f"合计已适配：{len(goal_v1) + len(brain)} 项")

wl_goal = [m for m in goal_v1 if m.get("default_whitelisted")]
wl_brain = [m for m in brain if m.get("default_whitelisted")]
print(f"\n默认白名单：{len(wl_goal) + len(wl_brain)} 项 "
      f"→ {[m['id'] for m in wl_goal + wl_brain]}")

print("\n" + "=" * 78)
print("Goal 系（%d）" % len(goal_v1))
print("=" * 78)
for i, m in enumerate(sorted(goal_v1, key=lambda x: x["id"]), 1):
    wl = " 🔒默认白名单" if m.get("default_whitelisted") else ""
    sp = " ⚠️特殊适配" if m["id"] in special else ""
    print(f"  {i:>2}. minecraft:{m['id']:<24} {m['zh']:<10}{wl}{sp}")

print("\n" + "=" * 78)
print("Brain 系（%d）" % len(brain))
print("=" * 78)
for i, m in enumerate(sorted(brain, key=lambda x: x["id"]), 1):
    wl = " 🔒默认白名单" if m.get("default_whitelisted") else ""
    sp = " ⚠️特殊适配" if m["id"] in special else ""
    print(f"  {i:>2}. minecraft:{m['id']:<24} {m['zh']:<10}{wl}{sp}")

print("\n" + "=" * 78)
print("特殊适配说明（%d）" % len(special))
print("=" * 78)
for k, v in special.items():
    mark = "⏸ v1.0 暂缓" if k in DEFER else ""
    print(f"  {k:<18} {v}  {mark}")

# 产出 Java 常量片段
print("\n" + "=" * 78)
print("Java 代码常量（供 dev 阶段直接使用）")
print("=" * 78)
print("""
public final class AdaptedMobRegistry {
    /** Goal 系：通过 goalSelector.removeAllGoals(Predicate) 移除主动索敌 */
    public static final Set<EntityType<?>> GOAL_BASED = Set.of(""")
for m in sorted(goal_v1, key=lambda x: x["id"]):
    print(f"        EntityType.{m['id'].upper()},   // {m['zh']}")
print("""    );

    /** Brain 系：擦除 ANGRY_AT / ATTACK_TARGET 记忆 */
    public static final Set<EntityType<?>> BRAIN_BASED = Set.of(""")
for m in sorted(brain, key=lambda x: x["id"]):
    print(f"        EntityType.{m['id'].upper()},   // {m['zh']}")
print("""    );

    /** 默认白名单：已适配但默认保持原版行为，管理员可移出 */
    public static final Set<EntityType<?>> DEFAULT_WHITELIST = Set.of(""")
for m in sorted(wl_goal + wl_brain, key=lambda x: x["id"]):
    print(f"        EntityType.{m['id'].upper()},   // {m['zh']}")
print("    );\n}")

out = {
    "version": "v1.0",
    "mc_version": data["mc_version"],
    "total_adapted": len(goal_v1) + len(brain),
    "goal_based": [m["id"] for m in sorted(goal_v1, key=lambda x: x["id"])],
    "brain_based": [m["id"] for m in sorted(brain, key=lambda x: x["id"])],
    "default_whitelist": [m["id"] for m in sorted(wl_goal + wl_brain, key=lambda x: x["id"])],
    "deferred_v1_1": [m["id"] for m in deferred],
    "special_adaptations": special,
}
dst = BASE / "adapted_mobs_v1.json"
dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n✅ 已写入 {dst.name}")
