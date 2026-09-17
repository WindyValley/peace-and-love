package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.TargetGoal;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;
import top.windyvalley.peaceandlove.scope.AlertScope;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;

/**
 * Goal 系中立化策略 —— 移除主动索敌 Goal，保留受击反击与攻击执行 Goal。
 *
 * <p>传统 {@code GoalSelector} 体系（僵尸、骷髅、蜘蛛等绝大多数生物）。
 *
 * <h2>目标选择器（targetSelector）处理</h2>
 * 移除除 {@link HurtByTargetGoal} 外的所有 {@link TargetGoal}（NearestAttackable*
 * 等主动索敌），使生物不再主动找玩家；<b>保留 HurtByTargetGoal</b>（被打反击）。
 * MeleeAttackGoal/RangedAttackGoal 等在 {@code goalSelector} 的攻击执行器一律不动
 * （参考末影人/北极熊/熊猫：中立生物保留攻击 Goal，只删主动索敌）。
 *
 * <h2>同族示警接入（见 {@link AlertScope}）</h2>
 * <ul>
 *   <li>A 类原生会示警：goal 不动，范围由 HurtByTargetGoalMixin 在玩家攻击时收窄；</li>
 *   <li>B 类有 HurtBy 但未开示警：把该构造期注册 goal 的 {@code alertSameType}
 *       置 true，进入 alertOthers 路径（Mixin 统一收窄、仅玩家触发）；</li>
 *   <li>C 类无 HurtBy：不在此补 goal（运行时新增 goal 触发不可靠、且会越权添加
 *       非玩家反击），自身反击与同族示警均由 AngerController 在玩家攻击路径处理。</li>
 * </ul>
 *
 * <p>本策略是注册到 StrategyRegistry 的<b>单例</b>，per-mob 改动（被移除 goal
 * 快照、被打开的示警开关）按 UUID 存入字段，restore 时逐项回滚。
 */
public final class GoalBasedStrategy implements NeutralizationStrategy {

    /** 要移除的主动索敌 Goal：所有 TargetGoal，但保留 HurtByTargetGoal（受击反击）。 */
    private static final Predicate<Goal> TARGET_GOAL_TO_REMOVE =
            g -> g instanceof TargetGoal && !(g instanceof HurtByTargetGoal);

    /** 被移除 Goal 的快照：UUID → 快照列表。 */
    private final Map<UUID, List<GoalSnapshot>> removedSnapshots = new ConcurrentHashMap<>();
    /** B 类中被本策略打开 alertSameType 的生物 UUID（restore 时置回 false）。 */
    private final Set<UUID> alertFlagToggled = ConcurrentHashMap.newKeySet();
    /** 已处理过的生物 UUID（幂等）。 */
    private final Set<UUID> processed = ConcurrentHashMap.newKeySet();

    @Override
    public boolean supports(EntityType<?> type) {
        // 兜底：凡已适配、且非 Brain 系特例者，均由本策略处理。
        return AdaptedMobs.GOAL_BASED.contains(type);
    }

    @Override
    public void neutralize(Mob mob) {
        UUID id = mob.getUUID();
        if (!processed.add(id)) {
            return; // 已中立化过，幂等
        }

        // 1) 先快照，后移除主动索敌 Goal（保留 HurtByTargetGoal）
        List<GoalSnapshot> removed =
                GoalSnapshot.capture(MobAccess.targetSelectorOf(mob), TARGET_GOAL_TO_REMOVE);
        removedSnapshots.put(id, removed);
        MobAccess.targetSelectorOf(mob).removeAllGoals(TARGET_GOAL_TO_REMOVE);

        // 2) B 类：打开构造期 HurtByTargetGoal 的同族示警开关
        boolean toggled = installKinAlert(mob);
        if (toggled) {
            alertFlagToggled.add(id);
        }

        // 3) 清掉当前目标，避免生物继续追杀中立化前已瞄准的玩家
        mob.setTarget(null);

        PeaceAndLove.LOGGER.info(
                "[中立化] {} 移除 {} 个主动索敌Goal{}",
                EntityType.getKey(mob.getType()), removed.size(),
                toggled ? "，已开启同族示警" : "");
    }

    /**
     * B 类：把保留下来的 HurtByTargetGoal 的 alertSameType 置 true。
     *
     * @return 是否确实打开了某个 HurtByTargetGoal 的开关
     */
    private boolean installKinAlert(Mob mob) {
        if (!AlertScope.ENABLE_ALERT_FLAG.contains(mob.getType())) {
            return false;
        }
        for (var wrapped : MobAccess.targetSelectorOf(mob).getAvailableGoals()) {
            Goal g = wrapped.getGoal();
            // 一只生物至多一个 HurtByTargetGoal，命中即止
            if (g instanceof HurtByTargetGoal && MobAccess.setAlertSameType(g, true)) {
                return true;
            }
        }
        return false;
    }

    @Override
    public void restore(Mob mob) {
        UUID id = mob.getUUID();
        if (!processed.remove(id)) {
            return; // 从未中立化或已还原
        }

        // 1) 被本策略打开的 alertSameType 置回 false（B 类；goal 仍在 selector 中）
        if (alertFlagToggled.remove(id)) {
            for (var wrapped : MobAccess.targetSelectorOf(mob).getAvailableGoals()) {
                if (wrapped.getGoal() instanceof HurtByTargetGoal) {
                    MobAccess.setAlertSameType(wrapped.getGoal(), false);
                }
            }
        }

        // 2) 原样塞回被移除的主动索敌 goal
        List<GoalSnapshot> removed = removedSnapshots.remove(id);
        if (removed != null) {
            GoalSnapshot.restore(MobAccess.targetSelectorOf(mob), removed);
        }

        PeaceAndLove.LOGGER.info("[中立化] 已还原 {}", EntityType.getKey(mob.getType()));
    }
}
