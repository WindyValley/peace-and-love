package top.windyvalley.peaceandlove.anger;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.NeutralMob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.ai.Brain;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;
import top.windyvalley.peaceandlove.scope.AlertScope;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 玩家攻击引发的<b>额外</b>仇恨与同族示警 —— T-ANGER-002/003。
 *
 * <p>注意职责边界：本类<b>不</b>负责“是否允许反击”。
 * 任何合法伤害源仍应走原版受击反击链；只有「玩家归因」的伤害
 * 才在这里额外记录仇恨来源、锁定玩家目标，并触发同族示警。
 */
public final class AngerController {

    private AngerController() {
    }

    /** 每只 Goal 系生物的剩余仇恨 tick（NeutralMob 系由原版自管）。 */
    private static final Map<UUID, Integer> angerTickByMob = new ConcurrentHashMap<>();

    /** 每只生物当前的仇恨来源（NONE 即中立，可交易）。 */
    private static final Map<UUID, AngerSource> angerSourceByMob = new ConcurrentHashMap<>();

    /**
     * Brain 系「最后攻击来源玩家 UUID」。
     *
     * <p>为何需要：玩家跑远、目标不可达时，原版 Brain 会自己清掉 ATTACK_TARGET
     * 记忆（getTarget 也变 null）。若只靠目标记忆做脱战距离判定，此时两条都
     * 解析不到玩家，“跑远立刻脱战”就永远不触发。记下最后攻击玩家后，仍能据
     * 其 UUID 在世界里找回玩家、算距离。仅仇恨期内存在，calmDown 清除。
     */
    private static final Map<UUID, UUID> lastAttackerByMob = new ConcurrentHashMap<>();

    /**
     * 玩家攻击时调用：记录仇恨来源并触发同族示警。
     *
     * <p>前提是生物已被中立化；非玩家伤害不应走到这里，
     * 仍由原版受击反击链自行处理。
     */
    public static void onPlayerAttack(Mob mob, Player attacker) {
        if (!NeutralizationScope.isNeutralized(mob.getType(), PeaceAndLove.config().get())) {
            return;
        }

        // 玩家攻击的额外效果：把目标锁到攻击者本人，并记录仇恨来源
        mob.setTarget(attacker);
        mob.setLastHurtByPlayer(attacker);

        // 仇恨计时：Brain 系一律用 mod 计时（即使是 NeutralMob），与 BrainKinAlerter
        // 及 tickDecay 保持一致；Goal 系 NeutralMob 走原版 persistentAnger。
        if (AdaptedMobs.BRAIN_BASED.contains(mob.getType())) {
            angerTickByMob.put(mob.getUUID(), cooldownTicks());
        } else if (mob instanceof NeutralMob neutral) {
            neutral.setPersistentAngerTarget(attacker.getUUID());
            neutral.startPersistentAngerTimer();
        } else {
            angerTickByMob.put(mob.getUUID(), cooldownTicks());
        }

        setAngerSource(mob, AngerSource.PLAYER_DIRECT);
        if (AdaptedMobs.BRAIN_BASED.contains(mob.getType())) {
            lastAttackerByMob.put(mob.getUUID(), attacker.getUUID());
        }

        // 同族示警：
        //  - A/B 类（Goal 系）：带构造期 HurtByTargetGoal，受击后原版 start()→alertOthers，
        //    由 HurtByTargetGoalMixin 统一收窄半径，这里不重复；
        //  - C 类（Goal 系，巨人/守卫者/恶魂/史莱姆等）：无可用示警 goal，
        //    直接调 KinAlerter；
        //  - Brain 系（6 种）：攻击只认 ATTACK_TARGET 记忆，走 BrainKinAlerter
        //    （标 KIN_ALERT 让门控放行，再写攻击记忆）。
        if (AlertScope.requiresDirectAlert(mob.getType())) {
            KinAlerter.alert(mob, attacker);
        } else if (AdaptedMobs.BRAIN_BASED.contains(mob.getType())) {
            BrainKinAlerter.alert(mob, attacker);
        }
    }

    /** 脱战：恢复中立（清空目标、Brain 攻击记忆与仇恨，回到可交易状态）。 */
    public static void calmDown(Mob mob) {
        if (mob instanceof NeutralMob neutral) {
            neutral.stopBeingAngry();
        }
        // Brain 系攻击只认 Brain 记忆：setTarget(null) 不够，必须擦除
        // ATTACK_TARGET（猪灵系再擦 ANGRY_AT），否则脱战后仍一直追。
        // eraseMemory 带空值，源头门控对空值一律放行，不会被自己拦下。
        if (AdaptedMobs.BRAIN_BASED.contains(mob.getType())) {
            Brain<?> brain = mob.getBrain();
            brain.eraseMemory(MemoryModuleType.ATTACK_TARGET);
            if (mob.getType() == EntityType.PIGLIN || mob.getType() == EntityType.PIGLIN_BRUTE) {
                brain.eraseMemory(MemoryModuleType.ANGRY_AT);
            }
        }
        angerTickByMob.remove(mob.getUUID());
        lastAttackerByMob.remove(mob.getUUID());
        mob.setTarget(null);
        setAngerSource(mob, AngerSource.NONE);
    }

    /** Brain 同族示警路径调用：记下最后攻击玩家（与直接受击路径一致）。 */
    public static void rememberLastAttacker(Mob mob, Player attacker) {
        lastAttackerByMob.put(mob.getUUID(), attacker.getUUID());
    }

    // ── 仇恨来源存取（供脱战/示警/调试判定）─────────────────────────

    public static AngerSource angerSourceOf(Mob mob) {
        return angerSourceByMob.getOrDefault(mob.getUUID(), AngerSource.NONE);
    }

    public static void setAngerSource(Mob mob, AngerSource source) {
        if (source == AngerSource.NONE) {
            angerSourceByMob.remove(mob.getUUID());
        } else {
            angerSourceByMob.put(mob.getUUID(), source);
        }
    }

    // ── T-ANGER-004 脱战冷却（Goal 系计时存取）──────────────────────

    /** Goal 系生物剩余仇恨 tick；无记录返回 0（已脱战）。 */
    public static int remainingAngerTick(UUID mobId) {
        return angerTickByMob.getOrDefault(mobId, 0);
    }

    /** 冷却期玩家再次攻击 → 重置计时（Goal 系）。 */
    public static void resetAngerTick(UUID mobId) {
        angerTickByMob.put(mobId, cooldownTicks());
    }

    /** 递减 Goal 系仇恨计时，返回剩余 tick（供每 tick 脱战判定）。 */
    public static int decrementAngerTick(UUID mobId) {
        return angerTickByMob.merge(mobId, -1, Integer::sum);
    }

    /** 测试可注入的冷却秒数覆盖；为 {@code null} 时仍读线上配置。 */
    private static Integer cooldownSecondsOverrideForTest = null;

    static void overrideCooldownSecondsForTest(Integer seconds) {
        cooldownSecondsOverrideForTest = seconds;
    }

    private static int currentCooldownSeconds() {
        if (cooldownSecondsOverrideForTest != null) {
            return cooldownSecondsOverrideForTest;
        }
        return PeaceAndLove.config().get().anger_cooldown_seconds();
    }

    /** 配置里的冷却秒数转 tick；0 = 永久（返回一个永不到期的极大值）。 */
    private static int cooldownTicks() {
        int seconds = currentCooldownSeconds();
        if (seconds <= 0) {
            return Integer.MAX_VALUE; // 永久仇恨
        }
        return seconds * 20;
    }

    // ── T-ANGER-004 脱战冷却：每 tick 判定 ──────────────────────────

    /** 配置里的脱战距离（格）。 */
    private static double cooldownDistanceSqr() {
        double d = PeaceAndLove.config().get().anger_cooldown_distance();
        return d * d;
    }

    /**
     * 每 tick 对一个生物做脱战判定（由 AngerDecayService 遍历调用）。
     *
     * <p>脱战条件（满足其一，设计 docs/02-design.md §3.6）：
     * <ol>
     *   <li>仇恨计时结束（Goal 系本类自管；NeutralMob 系原版自管，无需这里判）</li>
     *   <li>玩家脱离配置距离（默认 32 格）</li>
     * </ol>
     *
     * <p>脱战后调 {@link #calmDown} 清空目标与仇恨来源，回到中立可交易状态。
     * NeutralMob 系由原版 persistentAnger 计时自管，本方法只处理 Goal 系。
     */
    public static void tickDecay(Mob mob) {
        boolean brain = AdaptedMobs.BRAIN_BASED.contains(mob.getType());
        // Goal 系 NeutralMob（末影人等）由原版 persistentAnger 自管，跳过。
        // Brain 系即使实现 NeutralMob（猪灵/蛮兵）也统一走 mod 计时，
        // 否则原版愤怒到期不清 KIN_ALERT 来源与 Brain 记忆，残留永久仇恨。
        if (!brain && mob instanceof NeutralMob) {
            return;
        }
        UUID id = mob.getUUID();
        if (angerSourceOf(mob) == AngerSource.NONE) {
            return; // 本就中立
        }

        // 条件 2：目标玩家脱离距离。
        // Goal 系目标在 getTarget()；Brain 系目标在 ATTACK_TARGET 记忆里
        //（getTarget 常为 null），两种都要解析出来才能做距离判定。
        net.minecraft.world.entity.LivingEntity targetEnt = mob.getTarget();
        if (brain && targetEnt == null) {
            targetEnt = mob.getBrain().getMemory(MemoryModuleType.ATTACK_TARGET)
                    .filter(t -> t instanceof net.minecraft.world.entity.LivingEntity)
                    .map(t -> (net.minecraft.world.entity.LivingEntity) t)
                    .orElse(null);
        }
        // 仍无目标（玩家跑远、原版已清攻击记忆）：用最后攻击玩家 UUID 找回玩家
        if (brain && targetEnt == null && lastAttackerByMob.containsKey(mob.getUUID())) {
            UUID attackerId = lastAttackerByMob.get(mob.getUUID());
            if (mob.level() instanceof net.minecraft.server.level.ServerLevel sl) {
                targetEnt = sl.getServer().getPlayerList().getPlayer(attackerId);
            }
        }
        if (targetEnt instanceof Player player
                && mob.distanceToSqr(player) > cooldownDistanceSqr()) {
            calmDown(mob);
            return;
        }

        // 条件 1：仇恨计时结束（0/负数 = 永久仇恨，Integer.MAX_VALUE 永不到期）
        int remaining = remainingAngerTick(id);
        if (remaining == Integer.MAX_VALUE) {
            return; // 永久仇恨
        }
        if (decrementAngerTick(id) <= 0) {
            calmDown(mob);
        }
    }
}
