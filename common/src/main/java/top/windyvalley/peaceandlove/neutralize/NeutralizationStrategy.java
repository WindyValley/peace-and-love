package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;

/**
 * 中立化策略接口。
 *
 * <p>命名以设计文档为准（{@code NeutralizationStrategy}，非任务卡笔误的
 * {@code NeutralizeStrategy}）。职责：把一只敌对 Mob 改造成「不主动攻击、
 * 可交易」的中立生物，且可逆（白名单热重载时恢复原版行为）。
 *
 * <p>两套实现对应两套 AI 体系：
 * <ul>
 *   <li>{@code GoalBasedStrategy} —— 传统 Goal/GoalSelector 体系（绝大多数生物）</li>
 *   <li>{@code BrainBasedStrategy} —— Brain/Behavior 体系（村民、猪灵等新生物）</li>
 * </ul>
 *
 * <p>由 {@code StrategyRegistry} 按 {@link EntityType} 分派。
 *
 * <p>实现约束：{@code neutralize()} 必须先做 {@link GoalSnapshot} 再移除，
 * 否则 {@code restore()} 无法还原原版行为。
 */
public interface NeutralizationStrategy {

    /**
     * 该策略是否支持这种生物。
     *
     * <p>GoalBased 与 BrainBased 的 supports 互斥，一只 Mob 只会命中一个策略。
     */
    boolean supports(EntityType<?> type);

    /**
     * 中立化：移除主动索敌行为，使其不主动攻击玩家。
     *
     * <p>保留 {@code HurtByTargetGoal}（被打会反击），由愤怒系统另行接管。
     * 必须先快照后移除，保证可逆。
     */
    void neutralize(Mob mob);

    /**
     * 还原：恢复原版敌对行为（白名单热重载时调用）。
     *
     * <p>依赖 neutralize 时的快照。对从未中立化的 Mob 调用应为空操作。
     */
    void restore(Mob mob);
}
