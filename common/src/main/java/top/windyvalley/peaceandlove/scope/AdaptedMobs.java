package top.windyvalley.peaceandlove.scope;

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
            EntityType.ZOMBIE,            // 僵尸 (zombie)
            EntityType.ZOMBIE_VILLAGER,   // 僵尸村民 (zombie_villager)
            EntityType.HUSK,              // 尸壳 (husk)
            EntityType.DROWNED,           // 溺尸 (drowned)
            EntityType.ZOMBIFIED_PIGLIN,  // 僵尸猪灵 (zombified_piglin)
            EntityType.SKELETON,          // 骷髅 (skeleton)
            EntityType.WITHER_SKELETON,   // 凋灵骷髅 (wither_skeleton)
            EntityType.STRAY,             // 流浪者 (stray)
            EntityType.BOGGED,            // 沼骸 (bogged)
            EntityType.GIANT,             // 巨人 (giant)
            EntityType.SPIDER,            // 蜘蛛 (spider)
            EntityType.CAVE_SPIDER,       // 洞穴蜘蛛 (cave_spider)
            EntityType.CREEPER,           // 苦力怕 (creeper)
            EntityType.GHAST,             // 恶魂 (ghast)
            EntityType.BLAZE,             // 烈焰人 (blaze)
            EntityType.WITCH,             // 女巫 (witch)
            EntityType.SLIME,             // 史莱姆 (slime)
            EntityType.MAGMA_CUBE,        // 岩浆怪 (magma_cube)
            EntityType.ENDERMAN,          // 末影人 (enderman)
            EntityType.ENDERMITE,         // 末影螨 (endermite)
            EntityType.GUARDIAN,          // 守卫者 (guardian)
            EntityType.ELDER_GUARDIAN,    // 远古守卫者 (elder_guardian)
            EntityType.ILLUSIONER,        // 幻术师 (illusioner)
            EntityType.RAVAGER,           // 劫掠兽 (ravager)
            EntityType.SILVERFISH,        // 蠹虫 (silverfish)
            EntityType.SHULKER,           // 潜影贝 (shulker)
            EntityType.PHANTOM,           // 幻翼 (phantom)
            EntityType.PILLAGER,          // 掠夺者 (pillager)
            EntityType.VINDICATOR,        // 卫道士 (vindicator)
            EntityType.EVOKER,            // 唤魔者 (evoker)
            EntityType.VEX,               // 恼鬼 (vex)
            EntityType.WITHER            // 凋灵 (wither)
    );

    /** Brain 系已适配生物，6 个：猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽/监守者/旋风人。 */
    public static final Set<EntityType<?>> BRAIN_BASED = Set.of(
            EntityType.PIGLIN,            // 猪灵 (piglin)
            EntityType.PIGLIN_BRUTE,      // 猪灵蛮兵 (piglin_brute)
            EntityType.HOGLIN,            // 疣猪兽 (hoglin)
            EntityType.ZOGLIN,            // 僵尸疣猪兽 (zoglin)
            EntityType.WARDEN,            // 监守者 (warden)
            EntityType.BREEZE            // 旋风人 (breeze)
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

    /** 已适配总数，供测试断言。 */
    public static int count() {
        return ALL.size();
    }
}
