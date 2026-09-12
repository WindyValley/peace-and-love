package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * T-NEUT-001：GoalSnapshot 快照/还原 + StrategyRegistry 分派。
 *
 * <p>Goal/GoalSelector 是 MC 类，需 Bootstrap 引导。
 * 用一个最小 Goal 子类做快照对象（Goal 抽象类，需 canUse）。
 */
class GoalSnapshotAndRegistryTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    /** 最小可用 Goal：canUse 恒 true。 */
    static final class DummyGoal extends Goal {
        private final String name;

        DummyGoal(String name) {
            this.name = name;
        }

        @Override
        public boolean canUse() {
            return true;
        }

        @Override
        public String toString() {
            return name;
        }
    }

    // ───────────────────────── GoalSnapshot ─────────────────────────

    @Test
    void 快照记录优先级与Goal实例() {
        GoalSelector selector = new GoalSelector(() -> null);
        Goal g1 = new DummyGoal("g1");
        Goal g2 = new DummyGoal("g2");
        selector.addGoal(1, g1);
        selector.addGoal(5, g2);

        List<GoalSnapshot> snaps = GoalSnapshot.capture(selector, g -> true);
        assertEquals(2, snaps.size());

        GoalSnapshot s1 = find(snaps, g1);
        assertEquals(1, s1.priority(), "优先级应被记录");
        assertSame(g1, s1.goal(), "应保持同一 Goal 实例引用");
    }

    @Test
    void 快照按谓词过滤() {
        GoalSelector selector = new GoalSelector(() -> null);
        Goal keep = new DummyGoal("keep");
        Goal skip = new DummyGoal("skip");
        selector.addGoal(1, keep);
        selector.addGoal(2, skip);

        List<GoalSnapshot> snaps = GoalSnapshot.capture(selector, g -> g == keep);
        assertEquals(1, snaps.size());
        assertSame(keep, snaps.get(0).goal());
    }

    @Test
    void 快照可原样还原() {
        GoalSelector selector = new GoalSelector(() -> null);
        Goal g = new DummyGoal("x");
        selector.addGoal(3, g);

        // 快照 → 清空 → 还原
        List<GoalSnapshot> snaps = GoalSnapshot.capture(selector, gg -> true);
        selector.removeAllGoals(gg -> true);
        assertEquals(0, selector.getAvailableGoals().size(), "移除后应为空");

        GoalSnapshot.restore(selector, snaps);
        assertEquals(1, selector.getAvailableGoals().size(), "还原后应恢复");
        // 还原的应是同一个 Goal 实例，且优先级一致
        var wrapped = selector.getAvailableGoals().iterator().next();
        assertSame(g, wrapped.getGoal());
        assertEquals(3, wrapped.getPriority());
    }

    private GoalSnapshot find(List<GoalSnapshot> snaps, Goal target) {
        return snaps.stream().filter(s -> s.goal() == target).findFirst().orElseThrow();
    }

    // ───────────────────────── StrategyRegistry ─────────────────────────

    private NeutralizationStrategy stub(boolean supports, String tag) {
        return new NeutralizationStrategy() {
            @Override
            public boolean supports(EntityType<?> type) {
                return supports;
            }

            @Override
            public void neutralize(net.minecraft.world.entity.Mob mob) {
            }

            @Override
            public void restore(net.minecraft.world.entity.Mob mob) {
            }

            @Override
            public String toString() {
                return tag;
            }
        };
    }

    @Test
    void 分派命中第一个supports的策略() {
        StrategyRegistry reg = new StrategyRegistry();
        var first = stub(true, "first");
        reg.register(first).register(stub(true, "second"));
        assertSame(first, reg.strategyFor(EntityType.ZOMBIE), "应命中先注册的");
    }

    @Test
    void 特例先于兜底注册则特例命中() {
        StrategyRegistry reg = new StrategyRegistry();
        var special = stub(true, "special");
        var fallback = stub(true, "fallback");
        // 特例先注册 → 命中特例，不落入兜底
        reg.register(special).register(fallback);
        assertSame(special, reg.strategyFor(EntityType.PIGLIN));
    }

    @Test
    void 跳过不supports的策略() {
        StrategyRegistry reg = new StrategyRegistry();
        reg.register(stub(false, "no")).register(stub(true, "yes"));
        assertEquals("yes", reg.strategyFor(EntityType.ZOMBIE).toString());
    }

    @Test
    void 无策略支持时抛异常() {
        StrategyRegistry reg = new StrategyRegistry();
        reg.register(stub(false, "no"));
        var ex = assertThrows(IllegalStateException.class,
                () -> reg.strategyFor(EntityType.ZOMBIE));
        assertTrue(ex.getMessage().contains("minecraft:zombie"), "异常应指出具体生物");
    }

    @Test
    void 注册表大小() {
        StrategyRegistry reg = new StrategyRegistry();
        assertEquals(0, reg.size());
        reg.register(stub(true, "a")).register(stub(true, "b"));
        assertEquals(2, reg.size());
    }
}
