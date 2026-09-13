package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import top.windyvalley.peaceandlove.PeaceAndLove;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.TargetGoal;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;

import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Goal 系中立化策略 —— 覆盖 32 个 Goal 系生物。
 *
 * <p>只移除一类 Goal：
 * <ul>
 *   <li><b>targetSelector 里的主动索敌 Goal</b>：{@code NearestAttackableTargetGoal}，
 *       及一切「非 {@code HurtByTargetGoal}」的 {@code TargetGoal}
 *       （含 {@code OwnerHurtTargetGoal} 护主类 —— 中立生物不该主动索敌）</li>
 * </ul>
 *
 * <p><b>明确保留两类 Goal</b>：
 * <ul>
 *   <li>{@code HurtByTargetGoal}：受击反击是设计要求，由 ANGER 模块统一接管</li>
 *   <li>{@code MeleeAttackGoal} / {@code RangedAttackGoal} 等攻击 Goal：
 *       它们只在 {@code mob.getTarget() != null} 时激活，负责寻路到目标并攻击。
 *       删除它们会导致 {@code HurtByTargetGoal} 虽设定目标但无法驱动移动——
 *       表现为「被打不反击」（mustReach 检查时 navigation 未激活）。
 *       参考末影人/北极熊/熊猫：中立生物保留攻击 Goal，只删主动索敌。</li>
 * </ul>
 *
 * <p><b>继承链依据</b>（check_goal_hierarchy.py 实测 + 原版中立生物验证）：
 * <pre>
 *   Goal
 *   ├── MeleeAttackGoal / RangedAttackGoal / ...   ← 保留（寻路+攻击执行器）
 *   └── TargetGoal
 *       ├── NearestAttackableTargetGoal   ← 移除（主动索敌）
 *       ├── HurtByTargetGoal              ← 保留（受击反击）
 *       ├── OwnerHurtTargetGoal           ← 移除（护主=主动索敌）
 *       └── DefendVillageTargetGoal       ← 移除
 * </pre>
 *
 * <p><b>可逆性</b>：移除前对 targetSelector 做 {@link GoalSnapshot}，
 * restore 时原样塞回。快照按 Mob 实例存于 {@link IdentityHashMap}（按引用，
 * 不用 equals，避免 Mob 复用 equals 的坑）。
 *
 * <p><b>幂等</b>：重复 neutralize 同一 Mob 不重复移除（谓词对已移除者不再命中），
 * 且快照只在首次捕获，后续调用不覆盖——restore 总能还原到最初状态。
 */
public class GoalBasedStrategy implements NeutralizationStrategy {

    /**
     * targetSelector 中应移除的主动索敌 Goal：一切 TargetGoal，
     * 但排除 HurtByTargetGoal（受击反击保留）。
     */
    private static final Predicate<Goal> TARGET_GOAL_TO_REMOVE = g ->
            g instanceof TargetGoal && !(g instanceof HurtByTargetGoal);

    /** 每只 Mob 的 targetSelector 快照。 */
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
        if (targetSnaps.containsKey(mob)) {
            return;
        }

        GoalSelector targetSel = MobAccess.targetSelectorOf(mob);

        // 先快照，后移除（顺序不可反，否则快照为空）
        List<GoalSnapshot> tSnap = GoalSnapshot.capture(targetSel, TARGET_GOAL_TO_REMOVE);
        targetSnaps.put(mob, tSnap);

        targetSel.removeAllGoals(TARGET_GOAL_TO_REMOVE);

        // 调试日志：打印移除/保留，定位「被打不反击」bug
        if (PeaceAndLove.LOGGER.isInfoEnabled()) {
            PeaceAndLove.LOGGER.info("[中立化] {} targetSelector 移除 {} 个主动索敌Goal: {}",
                    EntityType.getKey(mob.getType()), tSnap.size(), names(tSnap));
            PeaceAndLove.LOGGER.info("[中立化] {} targetSelector 保留: {}",
                    EntityType.getKey(mob.getType()), remaining(targetSel));
        }

        // 清掉当前目标，避免生物继续追杀已在瞄准的玩家
        mob.setTarget(null);
    }

    private static String names(List<GoalSnapshot> snaps) {
        return snaps.stream().map(s -> s.goal().getClass().getSimpleName()).toList().toString();
    }

    private static String remaining(GoalSelector sel) {
        java.util.List<String> out = new java.util.ArrayList<>();
        for (net.minecraft.world.entity.ai.goal.WrappedGoal w : sel.getAvailableGoals()) {
            out.add(w.getGoal().getClass().getSimpleName());
        }
        return out.toString();
    }

    @Override
    public void restore(Mob mob) {
        List<GoalSnapshot> t = targetSnaps.remove(mob);
        if (t == null) {
            return; // 从未中立化，空操作
        }
        GoalSnapshot.restore(MobAccess.targetSelectorOf(mob), t);
    }
}
