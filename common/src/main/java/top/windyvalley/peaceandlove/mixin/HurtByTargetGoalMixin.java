package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.anger.KinAlerter;
import top.windyvalley.peaceandlove.scope.AlertScope;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 同族示警范围干预 —— 复用原版 {@code HurtByTargetGoal.alertOthers} 机制。
 *
 * <p>原版 alertOthers 的通知半径写死为 {@code FOLLOW_RANGE}（僵尸 35、
 * 烈焰人 48…），且 AABB 立方体。本 Mixin 在该方法 HEAD 按生物分类处理：
 *
 * <ul>
 *   <li><b>未中立化</b>：直接放行，100% 原版行为。</li>
 *   <li><b>已中立化 + 玩家攻击</b>（A/B/C-Pathfinder 通用）：取消原版大范围
 *       通知，改走 {@link KinAlerter}（配置半径、球形精筛）。</li>
 *   <li><b>已中立化 + 非玩家伤害源</b>：
 *     <ul>
 *       <li>A 类（{@link AlertScope#NATIVE_ALERT}，原生会示警）：放行，保留
 *           原版「怪互打也呼朋引伴」的行为，模组只在玩家攻击时控难度；</li>
 *       <li>B/C-Pathfinder（{@link AlertScope#isModEnabledAlert}，示警由模组
 *           开启）：取消——设计要求这些生物仅玩家攻击才新增示警。</li>
 *     </ul>
 *   </li>
 * </ul>
 *
 * <p>注意：本 Mixin 只干预「通知同族」；生物自身的受击反击由
 * HurtByTargetGoal 的 start()/setTarget 负责，不在此方法内，不受影响。
 */
@Mixin(HurtByTargetGoal.class)
public abstract class HurtByTargetGoalMixin {

    @Inject(method = "alertOthers", at = @At("HEAD"), cancellable = true)
    private void peaceandlove$narrowAlertRange(CallbackInfo ci) {
        HurtByTargetGoal goal = (HurtByTargetGoal) (Object) this;
        Mob mob = ((TargetGoalAccessor) goal).peaceandlove$getMob();

        // 未中立化：完全原版
        if (!NeutralizationScope.isNeutralized(mob.getType(), PeaceAndLove.config().get())) {
            return;
        }

        if (mob.getLastHurtByMob() instanceof Player player) {
            // 玩家攻击：统一收窄到配置半径
            KinAlerter.alert(mob, player);
            ci.cancel();
            return;
        }

        // 非玩家伤害源：A 类保留原版示警，模组开启的 B/C 类取消
        if (AlertScope.isModEnabledAlert(mob.getType())) {
            ci.cancel();
        }
        // A 类：不 cancel，放行走原版
    }
}
