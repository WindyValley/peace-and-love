package top.windyvalley.peaceandlove.pricing;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.Items;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import top.windyvalley.peaceandlove.pricing.LootModel.Drop;
import top.windyvalley.peaceandlove.pricing.LootModel.EvaluatedEntry;
import top.windyvalley.peaceandlove.pricing.LootModel.EvaluatedPool;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * epk 纯函数 {@link DropExpectation} 测试 —— 直接喂中性 {@link EvaluatedPool}
 * （条件已折算为概率），不触碰 Mixin Accessor / codec，因此纯 JUnit 可跑。
 *
 * <p>真实 LootTable→EvaluatedPool 的<b>装配</b>（Accessor）与条件概率的真实性
 * 由真机 tests/automation 对黄金 70 条回归覆盖。
 */
class DropExpectationTest {

    @BeforeAll
    static void bootstrap() {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
    }

    private EvaluatedEntry item(net.minecraft.world.item.Item item, int weight,
                                double cond, double countExp, int countMax) {
        return new EvaluatedEntry(item,
                net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(item),
                weight, cond, false, countExp, countMax);
    }

    @Test
    void 单池单物品_rolls乘条件乘权重乘数量() {
        // rolls=1, pool条件=0.5, 该物品权重2/总权重5, entry条件=1, 数量期望=2
        // epk = 1 * 0.5 * (2/5) * 1 * 2 = 0.4
        EvaluatedPool pool = new EvaluatedPool(1.0, 0.5, false, 5, List.of(
                item(Items.ROTTEN_FLESH, 2, 1.0, 2.0, 2)));
        List<Drop> drops = DropExpectation.compute(List.of(pool));
        assertEquals(1, drops.size());
        assertEquals(0.4, drops.get(0).epk(), 1e-9);
        assertEquals(2, drops.get(0).countMax());
    }

    @Test
    void 多池叠加_同物品保留两条不合并() {
        // 两个池各产 1 个 slime_ball（互斥分支由条件概率折算，此处各 0.3）
        EvaluatedPool a = new EvaluatedPool(1, 1, false, 1, List.of(
                item(Items.SLIME_BALL, 1, 0.3, 1, 1)));
        EvaluatedPool b = new EvaluatedPool(1, 1, false, 1, List.of(
                item(Items.SLIME_BALL, 1, 0.3, 1, 1)));
        List<Drop> drops = DropExpectation.compute(List.of(a, b));
        assertEquals(2, drops.size(), "同物品跨池保留多条（对齐黄金基线 slime）");
        assertEquals(0.3, drops.get(0).epk(), 1e-9);
        assertEquals(0.3, drops.get(1).epk(), 1e-9);
    }

    @Test
    void 零期望产出被丢弃() {
        // 条件概率 0 → epk=0，不出行
        EvaluatedPool pool = new EvaluatedPool(1, 1, false, 1, List.of(
                item(Items.BONE, 1, 0.0, 1, 1)));
        assertTrue(DropExpectation.compute(List.of(pool)).isEmpty());
    }

    @Test
    void 总权重为零的池跳过不崩() {
        EvaluatedPool pool = new EvaluatedPool(1, 1, false, 0, List.of(
                item(Items.BONE, 0, 1, 1, 1)));
        assertTrue(DropExpectation.compute(List.of(pool)).isEmpty());
    }

    @Test
    void 保守估计标记透传() {
        EvaluatedPool pool = new EvaluatedPool(1, 1, false, 1, List.of(
                new EvaluatedEntry(Items.STRING,
                        net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(Items.STRING),
                        1, 0.3, true, 1, 1)));
        Drop d = DropExpectation.compute(List.of(pool)).get(0);
        assertTrue(d.approximated(), "entry 的 approximated 应透传到 Drop");
    }
}
