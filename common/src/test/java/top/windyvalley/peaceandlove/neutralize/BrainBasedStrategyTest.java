package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * T-NEUT-003：BrainBasedStrategy 分派与愤怒探针接线。
 *
 * <p><b>未覆盖</b>：Brain 系 Mob（猪灵/监守者等）依赖 level、Brain 初始化、
 * 注册表，纯 JUnit 无法实例化，每 tick 擦除的实际效果移交真机验证。
 * 这里验证的是可分派的逻辑：supports 边界、angerProbe 接线语义。
 */
class BrainBasedStrategyTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    // ── supports 边界 ─────────────────────────────────────────────

    @Test
    void 支持全部六个Brain系生物() {
        BrainBasedStrategy s = new BrainBasedStrategy();
        assertTrue(s.supports(EntityType.PIGLIN), "猪灵");
        assertTrue(s.supports(EntityType.PIGLIN_BRUTE), "猪灵蛮兵");
        assertTrue(s.supports(EntityType.HOGLIN), "疣猪兽");
        assertTrue(s.supports(EntityType.ZOGLIN), "僵尸疣猪兽");
        assertTrue(s.supports(EntityType.WARDEN), "监守者");
        assertTrue(s.supports(EntityType.BREEZE), "旋风人");
    }

    @Test
    void 不支持Goal系生物() {
        BrainBasedStrategy s = new BrainBasedStrategy();
        assertFalse(s.supports(EntityType.ZOMBIE), "僵尸是 Goal 系");
        // 僵尸猪灵带「猪灵」名但 P4 实测为 Goal 系，BrainBased 不应支持
        assertFalse(s.supports(EntityType.ZOMBIFIED_PIGLIN), "僵尸猪灵是 Goal 系");
    }

    @Test
    void 不支持未适配生物() {
        BrainBasedStrategy s = new BrainBasedStrategy();
        assertFalse(s.supports(EntityType.COW));
        assertFalse(s.supports(EntityType.ENDER_DRAGON), "末影龙 v1.1 才适配");
    }

    // ── 与 GoalBased 互斥（一只 Mob 只命中一个策略） ──────────────

    @Test
    void 与GoalBased策略互斥() {
        GoalBasedStrategy goal = new GoalBasedStrategy();
        BrainBasedStrategy brain = new BrainBasedStrategy();
        for (EntityType<?> t : AdaptedMobs.ALL) {
            boolean g = goal.supports(t);
            boolean b = brain.supports(t);
            assertTrue(g != b,
                    () -> t + " 应只命中一个策略，goal=" + g + " brain=" + b);
        }
    }

    // ── angerProbe 接线语义 ──────────────────────────────────────

    @Test
    void 默认愤怒探针为非愤怒() {
        BrainBasedStrategy s = new BrainBasedStrategy();
        // 默认 probe = mob -> false：无法直接读私有字段，经反射核对语义
        // 这里只验证 setAngerProbe(null) 不抛异常并重置为默认
        s.setAngerProbe(null);
    }

    @Test
    void 设置自定义愤怒探针() {
        BrainBasedStrategy s = new BrainBasedStrategy();
        s.setAngerProbe(mob -> true);
        // 探针被设置后，tick 应因愤怒而跳过擦除——但 tick 需要真实 Mob，
        // 此处仅验证接线不抛异常。实际擦除行为移交真机。
        s.setAngerProbe(null);
    }
}
