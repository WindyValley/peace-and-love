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

    // ── ✅ 应触发仇恨的 4 种 ────────────────────────────────────────

    @Test
    void 玩家直接攻击_触发() {
        // (isPlayer, _, _)
        assertTrue(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(true, false, false)));
    }

    @Test
    void 玩家投射物_触发() {
        // 玩家射出的箭：getEntity() 已解析为射箭玩家 → isPlayer=true
        assertTrue(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(true, false, false)));
    }

    @Test
    void 玩家的宠物_触发() {
        // ( _, isPlayerOwnedPet, _)
        assertTrue(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, true, false)));
    }

    @Test
    void 玩家点燃的TNT_触发() {
        // ( _, _, isPlayerLitTnt)
        assertTrue(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, false, true)));
    }

    // ── ❌ 不介入（走原版逻辑）的 5 种 ───────────────────────────────

    @Test
    void 铁傀儡攻击_不触发() {
        assertFalse(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 村民卫兵攻击_不触发() {
        // 与铁傀儡同为「非玩家归因」
        assertFalse(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 怪物内斗_不触发() {
        assertFalse(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 环境伤害_不触发() {
        // 跌落/岩浆/窒息/仙人掌：责任实体为 null 或非玩家
        assertFalse(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, false, false)));
    }

    @Test
    void 无责任实体_不触发() {
        // 等价 featuresOf(null) 的结果
        assertFalse(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, false, false)));
    }

    // ── 边界：多特征同时成立仍以「可归因玩家」为准 ──────────────────

    @Test
    void 宠物且主人是玩家_触发_即使不是玩家本人() {
        // 宠物攻击：isPlayer=false 但 isPlayerOwnedPet=true → 仍触发
        assertTrue(AttackSourceClassifier.shouldTrigger(
                new EntityFeatures(false, true, false)));
    }
}
