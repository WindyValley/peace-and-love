package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.anger.AngerController;
import top.windyvalley.peaceandlove.anger.AngerSource;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

import java.util.Set;

/**
 * Brain 系「攻击记忆」写入门控 —— 层级一：只拦会造成伤害的攻击记忆。
 *
 * <p>在 {@code Brain.setMemoryInternal} HEAD 调用：当满足下列全部条件时，
 * 这次写入被取消（从源头拒绝，取代「每 tick 擦除」）：
 * <ol>
 *   <li>记忆是攻击类：{@code ATTACK_TARGET}，猪灵系另有 {@code ANGRY_AT}；</li>
 *   <li>主人是当前<b>已中立化</b>的 Brain 系生物（适配 + 不在白名单）；</li>
 *   <li>主人当前<b>不处于愤怒</b>（anger source = NONE）。</li>
 * </ol>
 *
 * <p><b>愤怒反击放行</b>：玩家主动攻击后，主人的 anger source 在 hurt HEAD
 * 已被置为非 NONE，此后原版链路写入攻击记忆一律放行，反击照常。
 *
 * <p>层级一不拦监守者的怒吼目标/调查位置、旋风人的目标候选等架势类记忆，
 * 只保证攻击行为执行不了、玩家不掉血。
 */
public final class BrainAttackGate {

    /** 猪灵系额外需要拦截的记仇记忆。 */
    private static final Set<EntityType<?>> PIGLIN_FAMILY = Set.of(
            EntityType.PIGLIN, EntityType.PIGLIN_BRUTE);

    private BrainAttackGate() {
    }

    /**
     * @return true 表示这次记忆写入应被取消
     */
    public static boolean shouldBlock(LivingEntity owner, MemoryModuleType<?> memoryType) {
        if (!(owner instanceof Mob mob)) {
            return false;
        }
        if (!isAttackMemory(mob.getType(), memoryType)) {
            return false;
        }
        if (!NeutralizationScope.isNeutralized(mob.getType(), PeaceAndLove.config().get())) {
            return false;
        }
        // 愤怒中（玩家打过）放行反击；否则中立生物不该形成攻击
        return AngerController.angerSourceOf(mob) == AngerSource.NONE;
    }

    /** 该记忆对该生物是否属攻击类。 */
    private static boolean isAttackMemory(EntityType<?> type, MemoryModuleType<?> memoryType) {
        if (memoryType == MemoryModuleType.ATTACK_TARGET) {
            return true;
        }
        return memoryType == MemoryModuleType.ANGRY_AT && PIGLIN_FAMILY.contains(type);
    }

    /** 供注册/兜底判断：是否 Brain 系已适配生物。 */
    public static boolean isBrainMob(EntityType<?> type) {
        return AdaptedMobs.BRAIN_BASED.contains(type);
    }
}
