package top.windyvalley.peaceandlove.debug;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.NeutralMob;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import net.minecraft.world.entity.player.Player;
import top.windyvalley.peaceandlove.anger.AngerController;
import top.windyvalley.peaceandlove.anger.AngerSource;
import top.windyvalley.peaceandlove.config.PalConfig;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 从服务端运行时的 {@link Mob} 采集 {@link MobInspection} 诊断字段。
 *
 * <p><b>只读，不改变任何状态</b>。本类依赖 Minecraft 运行时（注册表、Mob、
 * Brain 记忆），无法纯 JUnit 构造，采集正确性移交真机验证；结论的组装与
 * 渲染在 {@link MobInspection} 中已被单测覆盖。
 *
 * <p>目标解析与 {@code AngerController.tickDecay} 保持同一套规则：Goal 系
 * 目标在 {@code getTarget()}，Brain 系常为 {@code null}、要回退读
 * {@code ATTACK_TARGET} 记忆，否则监守者/猪灵愤怒时会显示「无目标」。
 */
public final class MobInspector {

    private MobInspector() {
    }

    /** 采集一只生物的完整诊断快照。 */
    public static MobInspection inspect(Mob mob, PalConfig cfg) {
        EntityType<?> type = mob.getType();
        String id = BuiltInRegistries.ENTITY_TYPE.getKey(type).toString();

        boolean adapted = AdaptedMobs.isAdapted(type);
        boolean whitelisted = cfg.whitelistSet().contains(id);
        boolean brainBased = AdaptedMobs.BRAIN_BASED.contains(type);
        boolean boss = NeutralizationScope.isBoss(type);
        boolean neutralized = NeutralizationScope.isNeutralized(type, cfg);
        boolean canTrade = NeutralizationScope.canTrade(type, cfg);

        boolean angry = AngerController.isAngry(mob);
        String angerLabel = describeAngerSource(mob, brainBased, angry);
        boolean permanent = cfg.anger_cooldown_seconds() <= 0;
        double remainingSeconds = remainingAngerSeconds(mob, brainBased, angry);

        LivingEntity target = resolveTarget(mob, brainBased);
        String targetDesc = null;
        double targetDist = -1;
        if (target != null) {
            targetDesc = describeTarget(target);
            targetDist = Math.sqrt(mob.distanceToSqr(target));
        }

        return new MobInspection(
                id, adapted, whitelisted, brainBased, boss, neutralized, canTrade,
                angry, angerLabel, permanent, remainingSeconds,
                targetDesc, targetDist,
                cfg.anger_cooldown_seconds(), cfg.anger_cooldown_distance()
        );
    }

    /**
     * 解析当前攻击目标。
     *
     * <p>Brain 系生物（监守者/猪灵等）愤怒时 {@code getTarget()} 常为 null，
     * 真正目标在 ATTACK_TARGET 记忆里 —— 与 {@code AngerController} 的脱战
     * 距离判定回退路径一致。
     */
    private static LivingEntity resolveTarget(Mob mob, boolean brainBased) {
        LivingEntity target = mob.getTarget();
        if (target != null || !brainBased) {
            return target;
        }
        return mob.getBrain()
                .getMemory(MemoryModuleType.ATTACK_TARGET)
                .filter(t -> t instanceof LivingEntity)
                .map(t -> (LivingEntity) t)
                .orElse(null);
    }

    private static String describeTarget(LivingEntity target) {
        if (target instanceof Player player) {
            return "玩家 " + player.getGameProfile().getName();
        }
        return BuiltInRegistries.ENTITY_TYPE.getKey(target.getType()).toString();
    }

    /**
     * 仇恨来源标签。
     *
     * <p>mod 自管来源（PLAYER_DIRECT/KIN_ALERT）优先；其次区分原版 NeutralMob
     * 自带愤怒（如末影人被凝视、僵尸猪灵被玩家挑衅）与 Brain 攻击记忆残留。
     */
    private static String describeAngerSource(Mob mob, boolean brainBased, boolean angry) {
        if (!angry) {
            return "NONE";
        }
        AngerSource source = AngerController.angerSourceOf(mob);
        if (source != AngerSource.NONE) {
            return switch (source) {
                case PLAYER_DIRECT -> "玩家直接攻击";
                case KIN_ALERT -> "同族示警";
                default -> source.name();
            };
        }
        if (mob instanceof NeutralMob neutral && neutral.getRemainingPersistentAngerTime() > 0) {
            return "原版愤怒（凝视/挑衅等）";
        }
        if (brainBased) {
            return "Brain 攻击记忆";
        }
        return "UNKNOWN";
    }

    /**
     * 剩余仇恨秒数。
     *
     * <p>与脱战计时归属一致：Brain 系一律读 mod 计时；Goal 系里的
     * {@link NeutralMob}（末影人等）读原版 persistentAnger；其余 Goal 系
     * 读 mod 计时。无在途计时返回 -1（交给渲染层决定是否显示）。
     */
    private static double remainingAngerSeconds(Mob mob, boolean brainBased, boolean angry) {
        if (!angry) {
            return -1;
        }
        if (!brainBased && mob instanceof NeutralMob neutral) {
            int t = neutral.getRemainingPersistentAngerTime();
            return t > 0 ? t / 20.0 : -1;
        }
        int ticks = AngerController.remainingAngerTick(mob.getUUID());
        if (ticks == Integer.MAX_VALUE || ticks <= 0) {
            return ticks == Integer.MAX_VALUE ? -1 : -1;
        }
        return ticks / 20.0;
    }

    /** 供命令层判定注视命中的是否为可检查实体（含末影龙多部分碰撞体）。 */
    public static Mob asMob(Entity entity) {
        if (entity instanceof Mob mob) {
            return mob;
        }
        if (entity instanceof net.minecraft.world.entity.boss.EnderDragonPart part) {
            return part.parentMob;
        }
        return null;
    }
}
