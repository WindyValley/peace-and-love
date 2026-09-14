package top.windyvalley.peaceandlove.anger;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.NeutralMob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.AABB;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 同族示警 —— T-ANGER-003。攻击一只，激怒附近同族。
 *
 * <p><b>规则</b>（设计 docs/02-design.md §3.6 + 任务卡）：
 * <ul>
 *   <li>仅同一 {@code EntityType} 被通知（僵尸不通知骷髅）</li>
 *   <li>被通知者仇恨目标 = <b>同一个攻击者</b>（非通知者）</li>
 *   <li><b>禁止链式传播</b>：被通知者不再通知它的邻居（靠
 *       {@code angerSource=KIN_ALERT} 标记，且示警不再递归调用 alert）</li>
 *   <li>球形判定：{@code distanceToSqr <= r*r}，不用 {@code AABB.inflate}
 *       的立方体（角上会多出约 73% 体积）</li>
 *   <li>半径 0 时完全禁用示警</li>
 *   <li>仅玩家攻击触发（NPC 攻击导致的受伤不示警——由调用方
 *       {@code AngerController.onPlayerAttack} 保证只有玩家路径才进这里）</li>
 * </ul>
 *
 * <p>⚠️ 风险点（任务卡标注）：链式截断是易错处。本实现靠「被通知者只
 * setAngerSource(KIN_ALERT)，不再调 alert」保证单层——示警逻辑只在
 * onPlayerAttack 里触发一次，KIN_ALERT 来源不再级联。
 */
public final class KinAlerter {

    private KinAlerter() {
    }

    /**
     * 单层示警：激怒 source 附近同 EntityType 的中立化生物，目标是同一攻击者。
     */
    public static void alert(Mob source, Player attacker) {
        double r = PeaceAndLove.config().get().kin_alert_radius();
        if (r <= 0) {
            return; // 半径 0 完全禁用
        }

        AABB box = source.getBoundingBox().inflate(r);
        var cfg = PeaceAndLove.config().get();

        source.level().getEntitiesOfClass(Mob.class, box,
                m -> m != source
                        && m.getType() == source.getType()                 // 严格同类
                        && m.distanceToSqr(source) <= r * r                // 球形而非立方体
                        && NeutralizationScope.isNeutralized(m.getType(), cfg)
        ).forEach(kin -> {
            kin.setTarget(attacker);
            kin.setLastHurtByPlayer(attacker);
            if (kin instanceof NeutralMob neutral) {
                neutral.setPersistentAngerTarget(attacker.getUUID());
                neutral.startPersistentAngerTimer();
            } else {
                // Goal 系：自维护仇恨计时（与 onPlayerAttack 同路径）
                AngerController.resetAngerTick(kin.getUUID());
            }
            // ★ 关键：标记 KIN_ALERT，不再向外示警（单层截断）
            AngerController.setAngerSource(kin, AngerSource.KIN_ALERT);
        });
    }
}
