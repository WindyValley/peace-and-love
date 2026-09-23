package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.Brain;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;

import java.util.Set;

/**
 * Brain 系中立化策略 —— 覆盖 6 个 Brain 系生物。
 *
 * <p>猪灵 / 猪灵蛮兵 / 疣猪兽 / 僵尸疣猪兽 / 监守者 / 旋风人。
 *
 * <p>Brain 系不用 GoalSelector 索敌，而是 Behavior 每 tick 读
 * {@code MemoryModuleType.ATTACK_TARGET}（猪灵系另读 {@code ANGRY_AT}），
 * 移除 Goal 对它们无效。持续生效点不在本类：由
 * {@code BrainMixin} 在记忆写入的源头（{@code setMemoryInternal}）按
 * {@link BrainAttackGate} 门控取消攻击记忆写入，取代旧的「每 tick 擦除」。
 *
 * <p>本类只负责实体加入世界时的<b>一次性清理</b>：清掉它出生时可能已经
 * 带有的攻击目标。之后新的写入全部由源头拦截挡下，愤怒反击（被玩家打）
 * 则在门控处放行。
 *
 * <p><b>API 依据</b>（javap 实测）：
 * {@code Brain.eraseMemory} public、{@code LivingEntity.getBrain()} public，
 * 无需反射。{@code eraseMemory} 携带空值，能正常通过源头门控。
 */
public class BrainBasedStrategy implements NeutralizationStrategy {

    /**
     * 猪灵系额外读取的记仇记忆（除 ATTACK_TARGET 外其它系只读 ATTACK_TARGET）。
     *
     * <p>只含 Brain 系猪灵。僵尸猪灵虽带「猪灵」名，但 P4 实测为
     * <b>Goal 系</b>（{@code AdaptedMobs.GOAL_BASED}），由 GoalBasedStrategy +
     * KinAlerter 接管，不经本策略，故不在此列。
     */
    private static final Set<EntityType<?>> PIGLIN_FAMILY = Set.of(
            EntityType.PIGLIN, EntityType.PIGLIN_BRUTE);

    @Override
    public boolean supports(EntityType<?> type) {
        return AdaptedMobs.BRAIN_BASED.contains(type);
    }

    @Override
    public void neutralize(Mob mob) {
        // 一次性清掉出生时已带有的攻击目标；之后新写入由 BrainMixin 源头拦截
        Brain<?> brain = mob.getBrain();
        brain.eraseMemory(MemoryModuleType.ATTACK_TARGET);
        if (PIGLIN_FAMILY.contains(mob.getType())) {
            brain.eraseMemory(MemoryModuleType.ANGRY_AT);
        }
        mob.setTarget(null);
    }

    @Override
    public void restore(Mob mob) {
        // 没有动过 Goal/Behavior 结构，源头拦截随白名单门控停止即恢复原版，
        // 无需结构还原，空操作。
    }
}
