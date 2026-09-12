"""
从 neutralization_plan_v3.json 生成 AdaptedMobs.java
====================================================
T-SCOPE-001 明确要求：从 JSON 生成，不要手敲，避免拼写错误。

不用 f-string（JavaDoc 里大量 {@code}/{@link} 花括号冲突），改用模板替换。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "spikes/r3-ai/neutralization_plan_v3.json"
OUT = ROOT / "common/src/main/java/top/windyvalley/peaceandlove/scope/AdaptedMobs.java"

# id -> EntityType 常量名的特例（以 1.21.1 EntityType 实际字段名为准）
SPECIAL = {
    "zombie_pigman": "ZOMBIFIED_PIGLIN",
    "zombified_piglin": "ZOMBIFIED_PIGLIN",
    "hoglin": "HOGLIN",
    "zoglin": "ZOGLIN",
    "piglin_brute": "PIGLIN_BRUTE",
    "breeze": "BREEZE",
}


def to_const(mob_id: str) -> str:
    return SPECIAL.get(mob_id, mob_id.upper())


def block(entries):
    lines = []
    for e in entries:
        const = to_const(e["id"])
        lines.append("            EntityType.%-18s // %s (%s)" % (const + ",", e["zh"], e["id"]))
    return "\n".join(lines)


data = json.loads(SRC.read_text(encoding="utf-8"))
goal = data["goal_system"]
brain = data["brain_system"]

print("goal_system:", len(goal))
print("brain_system:", len(brain))
for b in brain:
    print("  brain:", b["id"], b["zh"])

assert len(brain) == 6, "brain_system 应为 6，实际 %d" % len(brain)

# 末影龙 v1.1 才适配，v1.0 必须从已适配列表剔除（docs/02-design.md:159/575/584）
goal = [e for e in goal if e["id"] != "ender_dragon"]
assert len(goal) == 32, "剔除末影龙后 goal_system 应为 32，实际 %d" % len(goal)
print("已剔除末影龙（v1.1 才适配）")

# 用占位符避免花括号转义问题
JAVA_TEMPLATE = r"""package top.windyvalley.peaceandlove.scope;

import net.minecraft.world.entity.EntityType;

import java.util.Set;

/**
 * v1.0 已适配的 38 个敌对生物。
 *
 * <p><b>本文件由 spikes/r3-ai/neutralization_plan_v3.json 生成，勿手改。</b>
 * 生成脚本：spikes/design-verify/gen_adapted_mobs.py
 *
 * <p>「已适配」指代码层面有能力中立化这些生物。它与「是否生效」是两回事 ——
 * 实际是否中立化由双重门控决定（在已适配列表 AND 不在白名单），见
 * NeutralizationScope。
 *
 * <p>末影龙<b>不在</b>列表中 —— v1.0 未适配，其行为完全不受影响。
 *
 * <p>分组依据是底层 AI 系统（详见 ADR-004）：GOAL_BASED(32) 用 GoalSelector
 * 驱动，靠 removeAllGoals(Predicate) 移除索敌 Goal；BRAIN_BASED(6) 用 Brain
 * 驱动，需拦截 activity 更新。
 */
public final class AdaptedMobs {

    /** Goal 系已适配生物，32 个。 */
    public static final Set<EntityType<?>> GOAL_BASED = Set.of(
__GOAL_BLOCK__
    );

    /** Brain 系已适配生物，6 个：猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽/监守者/旋风人。 */
    public static final Set<EntityType<?>> BRAIN_BASED = Set.of(
__BRAIN_BLOCK__
    );

    /** 全部已适配生物的合并视图（不可变），供 O(1) 查询。 */
    public static final Set<EntityType<?>> ALL = union();

    private AdaptedMobs() {
    }

    private static Set<EntityType<?>> union() {
        Set<EntityType<?>> s = new java.util.HashSet<>(GOAL_BASED);
        s.addAll(BRAIN_BASED);
        return Set.copyOf(s);
    }

    /** 该生物是否已适配（O(1)）。 */
    public static boolean isAdapted(EntityType<?> type) {
        return ALL.contains(type);
    }

    /**
     * 已适配生物的注册名集合（如 "minecraft:zombie"），供白名单有效性校验。
     *
     * <p>惰性初始化：EntityType 反查 id 需要注册表已 bootstrap，
     * 不能在类加载期做。
     */
    public static Set<String> adaptedIds() {
        Set<String> ids = new java.util.HashSet<>();
        for (EntityType<?> t : ALL) {
            ids.add(net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE
                    .getKey(t).toString());
        }
        return Set.copyOf(ids);
    }

    /** 已适配总数，供测试断言。 */
    public static int count() {
        return ALL.size();
    }
}
"""

# Set.of 不允许尾随逗号：清掉块内最后一个 ", //" 形式的逗号
def strip_last_comma(blk):
    # 最后一行的形式是 "... EntityType.X,  // 注释"，去掉逗号
    head, _, tail = blk.rpartition(",")
    return head + tail

java = (JAVA_TEMPLATE
        .replace("__GOAL_BLOCK__", strip_last_comma(block(goal)))
        .replace("__BRAIN_BLOCK__", strip_last_comma(block(brain))))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(java, encoding="utf-8", newline="\n")
print("\n生成:", OUT.relative_to(ROOT))
print("GOAL_BASED=%d  BRAIN_BASED=%d  合计=%d" % (len(goal), len(brain), len(goal) + len(brain)))
