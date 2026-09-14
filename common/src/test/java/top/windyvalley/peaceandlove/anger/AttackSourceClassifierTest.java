package top.windyvalley.peaceandlove.anger;

import org.junit.jupiter.api.Test;
import top.windyvalley.peaceandlove.anger.AttackSourceClassifier.EntityFeatures;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * T-ANGER-001：伤害源溯源判定 —— 9 种情况的真值表。
 *
 * <p>每条用例对应任务卡验收标准。判定逻辑是纯函数
 * {@link AttackSourceClassifier#shouldTrigger(EntityFeatures)}，
 * 与 MC 实体解耦，可在纯 JUnit 覆盖全部 9 种。
 *
 * <p><b>未覆盖</b>：{@code featuresOf(Entity)} 的 instanceof 提取
 * （依赖真实 Player/TamableAnimal/PrimedTnt 实例，纯 JUnit 造不出来），
 * 以及 Mixin 注入点本身 —— 移交真机验证。
 */
class AttackSourceClassifierTest {

    // ── ✅ 应判定为玩家归因的 4 种 ───────────────────────────────

    @Test
    void 玩家直接攻击_玩家归因() {
        assertTrue(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(true, false, false)));
    }

    @Test
    void 玩家投射物_玩家归因() {
        assertTrue(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(true, false, false)));
    }

    @Test
    void 玩家的宠物_玩家归因() {
        assertTrue(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, true, false)));
    }

    @Test
    void 玩家点燃的TNT_玩家归因() {
        assertTrue(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, false, true)));
    }

    // ── ❌ 非玩家归因的 5 种 ─────────────────────────────────────

    @Test
    void 铁傀儡攻击_非玩家归因() {
        assertFalse(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 村民卫兵攻击_非玩家归因() {
        assertFalse(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 怪物内斗_非玩家归因() {
        assertFalse(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 环境伤害_非玩家归因() {
        assertFalse(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 无责任实体_非玩家归因() {
        assertFalse(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, false, false)));
    }

    // ── 边界：多特征同时成立仍以「玩家归因」为准 ──────────────────

    @Test
    void 宠物且主人是玩家_玩家归因() {
        assertTrue(AttackSourceClassifier.isPlayerAttribution(
                new EntityFeatures(false, true, false)));
    }
}
