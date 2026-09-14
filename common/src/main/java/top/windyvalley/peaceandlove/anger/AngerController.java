package top.windyvalley.peaceandlove.anger;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.NeutralMob;
import net.minecraft.world.entity.player.Player;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 仇恨状态机与单目标锁定 —— T-ANGER-002。
 *
 * <p><b>核心规则</b>：仇恨只锁定「攻击者本人」，不扩散到其他玩家或 NPC。
 *
 * <p><b>两条实现路径</b>（probe_neutralmob.py 实测，设计文档未覆盖的分流）：
 * <ul>
 *   <li><b>NeutralMob 系</b>（末影人/僵尸猪灵/狼/蜜蜂等，{@code instanceof NeutralMob}）：
 *       用原版 persistentAnger 机制（{@code setPersistentAngerTarget} +
 *       {@code startPersistentAngerTimer}），它自带「只记仇攻击者」语义与 NBT 持久化。</li>
 *   <li><b>Goal 系</b>（僵尸/骷髅/苦力怕等 32 个，<b>不</b>实现 NeutralMob）：
 *       原版 persistentAnger 用不了（强转会 ClassCastException），
 *       改用 {@code mob.setTarget(attacker)} + 受击反击链（T-NEUT-002 已铺好），
 *       仇恨计时由本类自维护（见 {@code angerTickByMob}）。</li>
 * </ul>
 *
 * <p><b>仇恨计时</b>：30 秒（600 tick）或玩家脱离 32 格后脱战恢复中立，
 * 0 秒 = 永久仇恨。计时存实体侧（NeutralMob 系由原版 NBT 持久化；
 * Goal 系由本类按 UUID 记，重启后不保留——可接受，重启脱战即合理）。
 *
 * <p><b>⚠️ 禁止</b>调用 {@code forgetCurrentTargetAndRefreshUniversalAnger()}：
 * 它有 universal anger（对所有玩家记仇）语义，违反「仇恨不扩散到其他玩家」。
 */
public final class AngerController {

    private AngerController() {
    }

    /** 每只 Goal 系生物的剩余仇恨 tick（NeutralMob 系由原版自管）。 */
    private static final Map<UUID, Integer> angerTickByMob = new ConcurrentHashMap<>();

    /** 每只生物当前的仇恨来源（NONE 即中立，可交易）。 */
    private static final Map<UUID, AngerSource> angerSourceByMob = new ConcurrentHashMap<>();

    /**
     * 唯一入口：仅玩家攻击触发（ADR-004 决策三）。
     *
     * <p>由 {@code LivingEntityHurtMixin} 在确认伤害源可归因到玩家后调用。
     */
    public static void onPlayerAttack(Mob mob, Player attacker) {
        if (!NeutralizationScope.isNeutralized(mob.getType(), PeaceAndLove.config().get())) {
            return;
        }

        // 单目标锁定：目标 = 攻击者本人
        mob.setTarget(attacker);
        mob.setLastHurtByPlayer(attacker);

        if (mob instanceof NeutralMob neutral) {
            // NeutralMob 系：用原版 persistentAnger（只记仇攻击者，NBT 持久化）
            neutral.setPersistentAngerTarget(attacker.getUUID());
            neutral.startPersistentAngerTimer();
        } else {
            // Goal 系：自维护仇恨计时（重启不保留，可接受）
            angerTickByMob.put(mob.getUUID(), cooldownTicks());
        }

        setAngerSource(mob, AngerSource.PLAYER_DIRECT);

        // 同族示警（T-ANGER-003）：单层非链式
        KinAlerter.alert(mob, attacker);
    }

    /** 脱战：恢复中立（清空目标与仇恨，回到可交易状态）。 */
    public static void calmDown(Mob mob) {
        if (mob instanceof NeutralMob neutral) {
            neutral.stopBeingAngry();
        }
        angerTickByMob.remove(mob.getUUID());
        mob.setTarget(null);
        setAngerSource(mob, AngerSource.NONE);
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
        if (mob instanceof NeutralMob) {
            return; // NeutralMob 系由原版计时自管
        }
        UUID id = mob.getUUID();
        if (angerSourceOf(mob) == AngerSource.NONE) {
            return; // 本就中立
        }

        // 条件 2：目标玩家脱离距离
        var target = mob.getTarget();
        if (target instanceof Player player
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
