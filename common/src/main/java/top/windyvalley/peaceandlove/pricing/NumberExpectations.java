package top.windyvalley.peaceandlove.pricing;

import net.minecraft.world.level.storage.loot.providers.number.BinomialDistributionGenerator;
import net.minecraft.world.level.storage.loot.providers.number.ConstantValue;
import net.minecraft.world.level.storage.loot.providers.number.NumberProvider;
import net.minecraft.world.level.storage.loot.providers.number.UniformGenerator;

/**
 * {@link NumberProvider} 的静态期望/上界 —— 不调用 {@code getFloat(LootContext)}，
 * 因而无需构造战利品上下文，可纯 JUnit 覆盖。
 *
 * <p>对齐 spike（price_algo_v3.py 的 num_expected / num_max）：
 * <ul>
 *   <li>{@link ConstantValue}：常量；</li>
 *   <li>{@link UniformGenerator}：(min+max)/2；</li>
 *   <li>{@link BinomialDistributionGenerator}：n × p；</li>
 *   <li>其余（ScoreboardValue / StorageValue 等运行时依赖）：无法静态求值，保守给 1。</li>
 * </ul>
 *
 * <p>适配生物的实体掉落表中 rolls 只出现常量与 uniform，set_count 只出现
 * constant/uniform，因此其余分支仅为防御性兜底。
 */
public final class NumberExpectations {

    private NumberExpectations() {
    }

    /** 求期望；嵌套 provider 递归。 */
    public static double expected(NumberProvider provider) {
        if (provider instanceof ConstantValue c) {
            return c.value();
        }
        if (provider instanceof UniformGenerator u) {
            return (expected(u.min()) + expected(u.max())) / 2.0;
        }
        if (provider instanceof BinomialDistributionGenerator b) {
            return expected(b.n()) * expected(b.p());
        }
        // 运行时计分板/存储依赖：静态不可求值，与 spike 一致保守给 1。
        return 1.0;
    }

    /**
     * set_count 数量期望，按原版 SetItemCountFunction「逐整数取值后 clamp 到 ≥0」
     * 的语义静态化：floor(min)..floor(max) 每个整数 max(0, x) 后平均。
     *
     * <p>这修正了 spike 缺陷②：uniform(0,1) 若直接 (0+1)/2 没错，但
     * uniform(-1,1) 必须按 (0+0+1)/3 算，不能出现负产出。
     */
    public static double expectedCountClamped(NumberProvider provider) {
        if (provider instanceof ConstantValue c) {
            return Math.max(0.0, c.value());
        }
        if (provider instanceof UniformGenerator u) {
            int lo = (int) Math.floor(expected(u.min()));
            int hi = (int) Math.floor(expected(u.max()));
            if (hi < lo) {
                return 0.0;
            }
            long sum = 0;
            for (int x = lo; x <= hi; x++) {
                sum += Math.max(0, x);
            }
            return (double) sum / (hi - lo + 1);
        }
        // 二项分布恒非负；其余兜底给期望本身（不为负的 provider）。
        return Math.max(0.0, expected(provider));
    }

    /** 数量上界（用于 TradeSpec.count，即单次交易产出 = looting 0 最大掉落量）。 */
    public static int maxCount(NumberProvider provider) {
        if (provider instanceof ConstantValue c) {
            return Math.max(1, (int) c.value());
        }
        if (provider instanceof UniformGenerator u) {
            return Math.max(1, (int) Math.floor(expected(u.max())));
        }
        if (provider instanceof BinomialDistributionGenerator b) {
            return Math.max(1, (int) Math.round(expected(b.n())));
        }
        return 1;
    }
}
