package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.Brain;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;

import java.util.Set;
import java.util.function.Predicate;

/**
 * Brain 系中立化策略 —— 覆盖 6 个 Brain 系生物。
 *
 * <p>猪灵 / 猪灵蛮兵 / 疣猪兽 / 僵尸疣猪兽 / 监守者 / 旋风人。
 *
 * <p>Brain 系不用 GoalSelector 索敌，而是 Behavior 每 tick 读
 * {@code MemoryModuleType.ATTACK_TARGET}（猪灵系另读 {@code ANGRY_AT}）。
 * 移除 Goal 对它们无效，故改为<b>每 tick 擦除攻击记忆</b>，让索敌
 * Behavior 拿不到目标而空转。
 *
 * <p><b>API 依据</b>（javap 实测）：
 * {@code Brain.eraseMemory}/{@code hasMemoryValue} 均 public，
 * {@code LivingEntity.getBrain()} public。无需反射。
 *
 * <p><b>关键设计——尊重仇恨</b>：当生物处于愤怒（被玩家攻击）时，
 * <b>不擦除</b>，允许它反击。否则中立化会连「被打反击」都禁掉，
 * 违反「受击反击由 ANGER 接管」的设计。愤怒判定由
 * {@link #angerProbe} 注入——T-NEUT 后续 AngerController 就绪后接线，
 * 默认「非愤怒」（v1.0 愤怒系统未接时退化为始终擦除）。
 *
 * <p><b>性能</b>：每实体每 tick 两次 hasMemoryValue + 至多两次 erase，
 * 均为 O(1) Map 操作。基线测量见测试。被擦除的生物集合用 {@code angered}
 * 兜底不需要——擦除本身幂等，重复擦无害。
 */
public class BrainBasedStrategy implements NeutralizationStrategy {

    /**
     * 猪灵系额外读取的愤怒记忆（除 ANGRY_AT 外其它系只读 ATTACK_TARGET）。
     *
     * <p>只含 Brain 系猪灵。僵尸猪灵虽带「猪灵」名，但 P4 实测为
     * <b>Goal 系</b>（{@code AdaptedMobs.GOAL_BASED}），由 GoalBasedStrategy +
     * KinAlerter 接管，不经本策略，故不在此列。
     */
    private static final Set<EntityType<?>> PIGLIN_FAMILY = Set.of(
            EntityType.PIGLIN, EntityType.PIGLIN_BRUTE);

    /**
     * 愤怒探针：返回 true 表示该 Mob 正处于愤怒（被打），本 tick 不擦除。
     * 由 AngerController 接线；默认「非愤怒」（始终擦除）。
     */
    private volatile Predicate<Mob> angerProbe = mob -> false;

    /** 接入愤怒判定（T-NEUT 后续任务调用）。 */
    public void setAngerProbe(Predicate<Mob> probe) {
        this.angerProbe = probe != null ? probe : mob -> false;
    }

    @Override
    public boolean supports(EntityType<?> type) {
        return AdaptedMobs.BRAIN_BASED.contains(type);
    }

    @Override
    public void neutralize(Mob mob) {
        // Brain 系无 Goal 可移除；中立化 = 进入「每 tick 擦除」状态。
        // 状态由外部分派循环驱动，这里先立即清一次，消除当前仇恨。
        eraseAttackMemory(mob);
        mob.setTarget(null);
    }

    @Override
    public void restore(Mob mob) {
        // Brain 系无可还原的移除项（没动 Goal/Behavior 结构），
        // 恢复 = 停止擦除。擦除由 tick 驱动，restore 后不再被调用即可。
        // 无需结构还原，空操作。
    }

    /**
     * 每 tick 拦截：擦除非愤怒生物的攻击记忆。
     *
     * <p>由 tick 事件对每个已适配 Brain 系 Mob 调用。
     * 这是中立化的实际生效点（neutralize 只做一次性清理）。
     */
    public void tick(Mob mob) {
        if (angerProbe.test(mob)) {
            return; // 愤怒中：允许反击，不擦
        }
        eraseAttackMemory(mob);
    }

    private void eraseAttackMemory(Mob mob) {
        Brain<?> brain = mob.getBrain();
        if (brain.hasMemoryValue(MemoryModuleType.ATTACK_TARGET)) {
            brain.eraseMemory(MemoryModuleType.ATTACK_TARGET);
        }
        if (PIGLIN_FAMILY.contains(mob.getType())
                && brain.hasMemoryValue(MemoryModuleType.ANGRY_AT)) {
            brain.eraseMemory(MemoryModuleType.ANGRY_AT);
        }
    }
}
