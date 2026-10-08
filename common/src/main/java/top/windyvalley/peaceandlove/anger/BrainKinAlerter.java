package top.windyvalley.peaceandlove.anger;

import net.minecraft.world.entity.EntitySelector;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.Brain;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.AABB;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * Brain 系同族示警 —— Goal 系 {@link KinAlerter} 的 Brain 对应物。
 *
 * <p>为什么不能复用 {@code KinAlerter}：它对同族做 {@code setTarget(玩家)}，
 * 而 Brain 怪不看 targetGoal，攻击只认 Brain 里的 {@code ATTACK_TARGET}
 * 记忆；直接写该记忆又会被 {@code BrainAttackGate} 拦下（同族自身没挨打、
 * anger source=NONE）。
 *
 * <p>解法（方案 B，与 Goal 系同一概念）：对半径内已中立化的同族 Brain 怪，
 * <ol>
 *   <li>把 anger source 标为 {@link AngerSource#KIN_ALERT} ——
 *       {@code BrainAttackGate} 本就认这个放行，无需新增“绕过”开关；</li>
 *   <li>往 Brain 写 {@code ATTACK_TARGET=攻击者}（猪灵系再写 {@code ANGRY_AT}），
 *       记忆带过期，防止脱战后残留成永久仇恨；</li>
 *   <li>单层：仅“玩家直接攻击”触发本方法，被叫醒者不再二次示警。</li>
 * </ol>
 * 几何与 {@link KinAlerter} 一致：AABB 粗筛 + 球形精筛、严格同类、
 * 只通知无目标者、跳过攻击者同盟。
 */
public final class BrainKinAlerter {

    /** 写入的攻击记忆保留时长（tick）；与仇恨计时一起兜底，过期自动消失。 */
    private static final long MEMORY_TTL_TICKS = 600L;

    /** 猪灵系额外写 ANGRY_AT。 */
    private static final java.util.Set<EntityType<?>> PIGLIN_FAMILY = java.util.Set.of(
            EntityType.PIGLIN, EntityType.PIGLIN_BRUTE);

    private BrainKinAlerter() {
    }

    /**
     * 单层示警：激怒 source 附近同运行时类的中立化 Brain 怪，目标锁定攻击者。
     */
    public static void alert(Mob source, Player attacker) {
        var cfg = PeaceAndLove.config().get();
        double r = cfg.kin_alert_radius();
        if (r <= 0) {
            return;
        }

        AABB box = source.getBoundingBox().inflate(r, 10.0, r);

        source.level().getEntitiesOfClass(Mob.class, box,
                kin -> kin != source
                        && AdaptedMobs.BRAIN_BASED.contains(kin.getType())
                        && kin.getClass() == source.getClass()
                        && !kin.getBrain().hasMemoryValue(MemoryModuleType.ATTACK_TARGET)
                        && !kin.isAlliedTo(attacker)
                        && EntitySelector.NO_SPECTATORS.test(kin)
                        && kin.distanceToSqr(source) <= r * r
                        && NeutralizationScope.isNeutralized(kin.getType(), cfg)
        ).forEach(kin -> enrage(kin, attacker));
    }

    /** 把单个 Brain 怪激怒到攻击者：写 Brain 攻击记忆 + 设仇恨来源与计时。 */
    private static void enrage(Mob kin, Player attacker) {
        Brain<?> brain = kin.getBrain();
        // 1. 先标 KIN_ALERT，再写记忆——门控读到非 NONE 即放行这次写入
        AngerController.setAngerSource(kin, AngerSource.KIN_ALERT);
        brain.setMemoryWithExpiry(MemoryModuleType.ATTACK_TARGET, attacker, MEMORY_TTL_TICKS);
        if (PIGLIN_FAMILY.contains(kin.getType())) {
            brain.setMemoryWithExpiry(MemoryModuleType.ANGRY_AT, attacker.getUUID(), MEMORY_TTL_TICKS);
        }

        // 2. 目标与仇恨（让怪锁定攻击者；与原版 hurt→愤怒路径一致）
        kin.setTarget(attacker);
        kin.setLastHurtByPlayer(attacker);
        // 统一用 AngerController 仇恨计时驱动脱战（即使是 NeutralMob 也不走原版
        // persistentAnger）：原版愤怒到期不会清 mod 的 KIN_ALERT 来源、
        // 也不擦 Brain 攻击记忆，会残留成永久仇恨。
        AngerController.resetAngerTick(kin.getUUID());
        AngerController.rememberLastAttacker(kin, attacker);
    }
}
