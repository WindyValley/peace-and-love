package top.windyvalley.peaceandlove.scope;

import net.minecraft.world.entity.EntityType;

import java.util.Set;

/**
 * 同族示警能力分类 —— 复用原版 {@code HurtByTargetGoal.alertOthers} 机制。
 *
 * <p>设计依据（源码核实，1.21.1 Mojmap）：原版怪物的同族示警能力分三档，
 * 本类据此决定中立化后如何接入统一示警链：
 *
 * <h2>A —— {@link #NATIVE_ALERT}：原生带示警链（setAlertOthers）</h2>
 * <p>受击会调用 {@code alertOthers()}，半径 = {@code FOLLOW_RANGE}
 * （僵尸 35、烈焰人 48 等，AABB 立方体、y 固定 ±10）。中立化后由
 * {@code HurtByTargetGoalMixin} 在<b>玩家攻击</b>时把半径收窄到配置
 * {@code kin_alert_radius}；非玩家攻击保持原版示警。
 *
 * <h2>B —— {@link #ENABLE_ALERT_FLAG}：有 HurtByTargetGoal 但没开 setAlertOthers</h2>
 * <p>只会自己反击、不通知同族（骷髅/蜘蛛/苦力怕/女巫/末影人/凋灵等）。
 * 它们的 HurtByTargetGoal 是<b>构造期注册</b>（触发可靠），中立化时把该 goal
 * 实例的 {@code alertSameType} 置 true，即进入与 A 相同的 alertOthers 路径，
 * Mixin 统一收窄半径。<b>仅玩家攻击</b>触发新增示警（非玩家源 Mixin 取消）。
 *
 * <h2>C —— {@link #DIRECT_ALERT}：连 HurtByTargetGoal 都没有</h2>
 * <p>巨人/守卫者/远古守卫者（PathfinderMob）与恶魂/史莱姆/岩浆怪/幻翼
 * （非 PathfinderMob，挂不上 HurtByTargetGoal）。这些生物：
 * <ul>
 *   <li>玩家攻击的<b>自身反击</b>：由 {@code AngerController.onPlayerAttack}
 *       统一 {@code setTarget}（它们的攻击执行 goal，如守卫者激光、史莱姆攻击，
 *       都在 goalSelector，中立化不删）；</li>
 *   <li><b>同族示警</b>：原版无示警入口，统一由 onPlayerAttack 直接调
 *       {@code KinAlerter}（已由 slime 真机验证可靠）；</li>
 *   <li>非玩家伤害：保持原版（这些怪原本就不因此反击/示警），不额外补 goal。</li>
 * </ul>
 * 不采用「运行时 addGoal(new HurtByTargetGoal)」：新增 goal 的
 * {@code start()→alertOthers()} 经实测触发不可靠（canUse 门控/注册时序），
 * 且会给原版从不反击的生物平白添加非玩家反击，属越权行为变更。
 *
 * <p>计数：A=15, B=10, C=7，合计 32 = Goal 系已适配总数。
 */
public final class AlertScope {

    private AlertScope() {
    }

    /** A：原生带 setAlertOthers 示警链。 */
    public static final Set<EntityType<?>> NATIVE_ALERT = Set.of(
            // 僵尸家族（ZombieVillager/Husk 继承 Zombie 的 registerGoals）
            EntityType.ZOMBIE,
            EntityType.ZOMBIE_VILLAGER,
            EntityType.HUSK,
            EntityType.DROWNED,
            EntityType.ZOMBIFIED_PIGLIN,
            // 其余原生 setAlertOthers
            EntityType.BLAZE,
            EntityType.ENDERMITE,
            EntityType.SILVERFISH,
            EntityType.SHULKER,
            // Raider 系互相通知
            EntityType.ILLUSIONER,
            EntityType.RAVAGER,
            EntityType.PILLAGER,
            EntityType.VINDICATOR,
            EntityType.EVOKER,
            EntityType.VEX
    );

    /** B：有 HurtByTargetGoal、无 setAlertOthers，中立化后置 alertSameType=true。 */
    public static final Set<EntityType<?>> ENABLE_ALERT_FLAG = Set.of(
            EntityType.SKELETON,
            EntityType.WITHER_SKELETON,
            EntityType.STRAY,
            EntityType.BOGGED,
            EntityType.SPIDER,
            EntityType.CAVE_SPIDER,
            EntityType.CREEPER,
            EntityType.WITCH,
            EntityType.ENDERMAN,
            EntityType.WITHER
    );

    /**
     * C：无 HurtByTargetGoal，同族示警由 AngerController 在玩家攻击路径直接调用。
     * 含 3 个 PathfinderMob（巨人/守卫者/远古守卫者）与 4 个非 PathfinderMob。
     */
    public static final Set<EntityType<?>> DIRECT_ALERT = Set.of(
            EntityType.GIANT,
            EntityType.GUARDIAN,
            EntityType.ELDER_GUARDIAN,
            EntityType.GHAST,
            EntityType.SLIME,
            EntityType.MAGMA_CUBE,
            EntityType.PHANTOM
    );

    /**
     * 该类型的同族示警是否必须由 AngerController 在玩家攻击路径直接调用
     * KinAlerter（而非经 HurtByTargetGoal.alertOthers）。即 C 类。
     */
    public static boolean requiresDirectAlert(EntityType<?> type) {
        return DIRECT_ALERT.contains(type);
    }

    /**
     * 该类型的示警是否由本模组在中立化时开启（B 类）。
     *
     * <p>B 类原生不示警，故<b>仅玩家攻击</b>才通知同族；非玩家伤害源时
     * Mixin 取消 alertOthers。A 类原生示警，非玩家源保留原版行为。
     */
    public static boolean isModEnabledAlert(EntityType<?> type) {
        return ENABLE_ALERT_FLAG.contains(type);
    }
}
