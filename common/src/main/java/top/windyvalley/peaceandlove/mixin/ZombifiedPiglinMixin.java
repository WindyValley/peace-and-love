package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.monster.ZombifiedPiglin;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 僵尸猪灵原版大范围群体报复拦截 —— T-NEUT-007。
 *
 * <p>僵尸猪灵有<b>两条互相独立的群体愤怒传播链</b>：
 * <ol>
 *   <li>受击瞬间 {@code HurtByTargetGoal.alertOthers()} —— 已由
 *       {@link HurtByTargetGoalMixin} 在玩家攻击时改道 {@code KinAlerter}
 *       （球形 {@code kin_alert_radius} 默认 4 格、单层、禁链式）；</li>
 *   <li>{@code ZombifiedPiglin#customServerAiStep()} 每 tick 调私有的
 *       {@code alertOthers()}：只要当前有目标，就按 {@code FOLLOW_RANGE}（35 格）
 *       AABB 把目标 {@code setTarget} 传染给周围所有同类，与第一条链无关。</li>
 * </ol>
 *
 * <p>第二条是 P4 验证点名的「双份示警」来源：玩家打一只，KinAlerter 已在 4 格内
 * 单层示警，原版这条又在 35 格内铺一层，范围远超设计。故在中立化且目标为玩家时
 * 取消它，群体报复统一归 KinAlerter。
 *
 * <p><b>非玩家源保留原版</b>（与 ADR-004 决策三、{@link HurtByTargetGoalMixin}
 * 的 A 类分支一致）：铁傀儡/怪物内斗引发的传染不干预，只有目标是玩家时才拦截。
 * 未中立化（白名单内）时 100% 原版。
 */
@Mixin(ZombifiedPiglin.class)
public abstract class ZombifiedPiglinMixin {

    @Inject(method = "alertOthers", at = @At("HEAD"), cancellable = true)
    private void peaceandlove$narrowHordeRetaliation(CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        if (!NeutralizationScope.isNeutralized(self.getType(), PeaceAndLove.config().get())) {
            return;
        }
        // 仅接管「对玩家」的大范围传染（4 格单层示警走 KinAlerter）；
        // 目标是非玩家生物（铁傀儡/怪物互斗）时保持原版。
        if (self.getTarget() instanceof Player) {
            ci.cancel();
        }
    }
}
