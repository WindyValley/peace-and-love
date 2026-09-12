package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.RangedAttackGoal;
import net.minecraft.world.entity.ai.goal.RangedBowAttackGoal;
import net.minecraft.world.entity.ai.goal.RangedCrossbowAttackGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.ai.goal.target.TargetGoal;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;

import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Goal 系中立化策略 —— 覆盖 32 个 Goal 系生物。
 *
 * <p>移除两类 Goal：
 * <ol>
 *   <li><b>goalSelector 里的攻击 Goal</b>：{@code MeleeAttackGoal} /
 *       {@code RangedAttackGoal} / {@code RangedBowAttackGoal} /
 *       {@code RangedCrossbowAttackGoal}</li>
 *   <li><b>targetSelector 里的索敌 Goal</b>：{@code NearestAttackableTargetGoal}，
 *       及一切「非 {@code HurtByTargetGoal}」的 {@code TargetGoal}
 *       （含 {@code OwnerHurtTargetGoal} 护主类 —— 中立生物不该主动索敌）</li>
 * </ol>
 *
 * <p><b>明确保留 {@code HurtByTargetGoal}</b>：受击反击是设计要求，
 * 由 ANGER 模块统一接管，不在中立化阶段移除。
 *
 * <p><b>继承链依据</b>（check_goal_hierarchy.py 实测）：
 * <pre>
 *   Goal
 *   ├── MeleeAttackGoal / RangedAttackGoal / RangedBowAttackGoal / RangedCrossbowAttackGoal
 *   └── TargetGoal
 *       ├── NearestAttackableTargetGoal   ← 移除
 *       ├── HurtByTargetGoal              ← 保留
 *       ├── OwnerHurtTargetGoal           ← 移除（护主=主动索敌）
 *       └── DefendVillageTargetGoal       ← 移除
 * </pre>
 *
 * <p><b>可逆性</b>：移除前对每个 selector 做 {@link GoalSnapshot}，
 * restore 时原样塞回。快照按 Mob 实例存于 {@link IdentityHashMap}（按引用，
 * 不用 equals，避免 Mob 复用 equals 的坑）。
 *
 * <p><b>幂等</b>：重复 neutralize 同一 Mob 不重复移除（谓词对已移除者不再命中），
 * 且快照只在首次捕获，后续调用不覆盖——restore 总能还原到最初状态。
 */
public class GoalBasedStrategy implements NeutralizationStrategy {

    /** goalSelector 中的攻击类 Goal。 */
    private static final Predicate<Goal> ATTACK_GOAL = g ->
            g instanceof MeleeAttackGoal
                    || g instanceof RangedAttackGoal
                    || g instanceof RangedBowAttackGoal
                    || g instanceof RangedCrossbowAttackGoal;

    /**
     * targetSelector 中应移除的索敌 Goal：一切 TargetGoal，
     * 但排除 HurtByTargetGoal（受击反击保留）。
     */
    private static final Predicate<Goal> TARGET_GOAL_TO_REMOVE = g ->
            g instanceof TargetGoal && !(g instanceof HurtByTargetGoal);

    /** 每只 Mob 的快照（goalSelector 与 targetSelector 分开记）。 */
    private final Map<Mob, List<GoalSnapshot>> goalSnaps = new IdentityHashMap<>();
    private final Map<Mob, List<GoalSnapshot>> targetSnaps = new IdentityHashMap<>();

    @Override
    public boolean supports(EntityType<?> type) {
        // 兜底：凡已适配、且非 Brain 系特例者，均由本策略处理。
        // BrainBased 特例须先于本策略注册到 StrategyRegistry。
        return AdaptedMobs.GOAL_BASED.contains(type);
    }

    @Override
    public void neutralize(Mob mob) {
        // 幂等：已中立化过的不再重复快照/移除
        if (goalSnaps.containsKey(mob)) {
            return;
        }

        GoalSelector goalSel = MobAccess.goalSelectorOf(mob);
        GoalSelector targetSel = MobAccess.targetSelectorOf(mob);

        // 先快照，后移除（顺序不可反，否则快照为空）
        goalSnaps.put(mob, GoalSnapshot.capture(goalSel, ATTACK_GOAL));
        targetSnaps.put(mob, GoalSnapshot.capture(targetSel, TARGET_GOAL_TO_REMOVE));

        goalSel.removeAllGoals(ATTACK_GOAL);
        targetSel.removeAllGoals(TARGET_GOAL_TO_REMOVE);

        // 清掉当前目标，避免生物继续追杀已在瞄准的玩家
        mob.setTarget(null);
    }

    @Override
    public void restore(Mob mob) {
        List<GoalSnapshot> g = goalSnaps.remove(mob);
        List<GoalSnapshot> t = targetSnaps.remove(mob);
        if (g == null && t == null) {
            return; // 从未中立化，空操作
        }
        if (g != null) {
            GoalSnapshot.restore(MobAccess.goalSelectorOf(mob), g);
        }
        if (t != null) {
            GoalSnapshot.restore(MobAccess.targetSelectorOf(mob), t);
        }
    }
}
