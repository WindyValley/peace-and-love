package top.windyvalley.peaceandlove.anger;

import net.minecraft.world.entity.EntitySelector;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.NeutralMob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.AABB;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 同族示警 —— 复用原版 {@code HurtByTargetGoal.alertOthers} 的分发语义。
 *
 * <p>设计（见 scope/AlertScope 分类）：原版 A 类怪自带示警链，B/C 类由本模组
 * 在中立化时接入；最终都汇到本方法，保证四组怪物示警行为一致。与原版的差异：
 * <ul>
 *   <li>半径取配置 {@code kin_alert_radius}（默认 4），而非原版的 FOLLOW_RANGE
 *       （僵尸 35、烈焰人 48…），用于控制难度；</li>
 *   <li>原版用 {@code AABB.inflate(d,10,d)} 立方体粗筛，角上会多通知约 73%
 *       体积的同族；本类在 AABB 粗筛后再加球形 {@code distanceToSqr <= r*r}
 *       精筛，边界更精确；</li>
 *   <li>仅通知<b>已中立化</b>的同族（未中立化者不被本模组干预）。</li>
 * </ul>
 *
 * <p><b>保留的原版语义</b>：严格同一运行时类（{@code source.getClass()}，
 * 僵尸不通知骷髅）、目标=攻击者本人、只通知当前无目标者、跳过攻击者同盟、
 * {@code setTarget} 由目标自身的攻击 Goal 接管移动，且原版 setTarget 不级联，
 * 天然单层（被通知者不会再次触发 alertOthers）。
 */
public final class KinAlerter {

    private KinAlerter() {
    }

    /**
     * 单层示警：激怒 source 附近同运行时类的中立化生物，目标是同一攻击者。
     *
     * @param source   被攻击的生物
     * @param attacker 攻击者（玩家）
     */
    public static void alert(Mob source, Player attacker) {
        var cfg = PeaceAndLove.config().get();
        double r = cfg.kin_alert_radius();
        if (r <= 0) {
            return; // 半径 0 完全禁用
        }

        // AABB 立方体粗筛（与原版一致，y 固定 ±10），随后球形精筛
        AABB box = source.getBoundingBox().inflate(r, 10.0, r);
        var finalCfg = cfg;

        source.level().getEntitiesOfClass(Mob.class, box,
                kin -> kin != source
                        && kin.getClass() == source.getClass()             // 严格同类（原版语义）
                        && kin.getTarget() == null                          // 原版：只通知无目标者
                        && !kin.isAlliedTo(attacker)                        // 原版：跳过攻击者同盟
                        && EntitySelector.NO_SPECTATORS.test(kin)
                        && kin.distanceToSqr(source) <= r * r               // 球形而非立方体
                        && NeutralizationScope.isNeutralized(kin.getType(), finalCfg)
        ).forEach(kin -> {
            // 与原版 alertOther 一致：直接 setTarget(攻击者)
            kin.setTarget(attacker);
            kin.setLastHurtByPlayer(attacker);
            if (kin instanceof NeutralMob neutral) {
                neutral.setPersistentAngerTarget(attacker.getUUID());
                neutral.startPersistentAngerTimer();
            } else {
                // Goal 系：自维护仇恨计时（与 onPlayerAttack 同路径）
                AngerController.resetAngerTick(kin.getUUID());
            }
            // 标记 KIN_ALERT（脱战/可观测性用；原版 setTarget 不级联，无需靠它截断）
            AngerController.setAngerSource(kin, AngerSource.KIN_ALERT);
        });
    }
}
