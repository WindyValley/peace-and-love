package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;

import java.util.ArrayList;
import java.util.List;

/**
 * 策略注册表 —— 按 EntityType 分派 NeutralizationStrategy。
 *
 * <p>注册顺序即优先级：先注册者先命中。GoalBased 是兜底（绝大多数生物），
 * BrainBased 等特例须先注册，否则会落入 GoalBased 兜底。
 *
 * <p>线程安全：注册仅发生在初始化期（单线程），查询发生在 tick（并发只读），
 * 故用不可变快照语义即可，无需加锁。
 */
public final class StrategyRegistry {

    private final List<NeutralizationStrategy> strategies = new ArrayList<>();

    /**
     * 注册策略。特例（BrainBased）先于兜底（GoalBased）注册。
     *
     * @return this，便于链式
     */
    public StrategyRegistry register(NeutralizationStrategy strategy) {
        strategies.add(strategy);
        return this;
    }

    /**
     * 按 EntityType 找到第一个 supports 的策略。
     *
     * @throws IllegalStateException 无任何策略支持（说明清单/策略实现有缺口）
     */
    public NeutralizationStrategy strategyFor(EntityType<?> type) {
        for (NeutralizationStrategy s : strategies) {
            if (s.supports(type)) {
                return s;
            }
        }
        throw new IllegalStateException(
                "无中立化策略支持 " + EntityType.getKey(type)
                        + " —— 已适配清单与策略实现不一致，请检查");
    }

    /** 注册的策略数（测试断言用）。 */
    public int size() {
        return strategies.size();
    }
}
