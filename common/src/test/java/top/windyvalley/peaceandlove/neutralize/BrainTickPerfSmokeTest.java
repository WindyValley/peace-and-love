package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * T-NEUT-003 性能基线：策略分派判定的开销 smoke。
 *
 * <p>源头拦截后不再有每 tick 的全服遍历；持续开销转移到 BrainMixin 里
 * 每次攻击记忆写入时的一次门控判定，须真机 profiling（spark）。
 * 这里量化纯 JUnit 可测的热路径——策略注册表的 supports 分派（Set.contains）。
 */
class BrainTickPerfSmokeTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    @Test
    void supports分派开销远低于1微秒() {
        BrainBasedStrategy brain = new BrainBasedStrategy();
        GoalBasedStrategy goal = new GoalBasedStrategy();

        // 预热 JIT
        for (int i = 0; i < 100_000; i++) {
            brain.supports(EntityType.PIGLIN);
            goal.supports(EntityType.ZOMBIE);
        }

        int iterations = 1_000_000;
        long t0 = System.nanoTime();
        boolean acc = false;
        for (int i = 0; i < iterations; i++) {
            // 模拟分派循环：每个实体两个策略各问一次
            acc |= brain.supports(EntityType.PIGLIN);
            acc |= goal.supports(EntityType.PIGLIN);
        }
        long elapsed = System.nanoTime() - t0;
        double nsPerDispatch = (double) elapsed / (iterations * 2.0);

        assertTrue(acc);
        System.out.printf("[perf] supports 分派: %.2f ns/次（%d 次循环）%n",
                nsPerDispatch, iterations * 2);

        // 1000 ns = 1μs 预算；supports 应远低于它（含 JIT 抖动留 10x 余量）
        assertTrue(nsPerDispatch < 1000,
                () -> String.format("supports 分派 %.0f ns 超 1μs 预算", nsPerDispatch));
    }
}
