package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.anger.AngerController;
import top.windyvalley.peaceandlove.anger.AttackSourceClassifier;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 仇恨触发点 —— T-ANGER-001。在受伤事件注入，<b>只有玩家攻击</b>才触发仇恨。
 *
 * <p>实测签名：{@code boolean hurt(DamageSource, float)}（1.21.1 混淆名 {@code a}，
 * spike 已确认）。注入 HEAD 并尽早返回，降低高频调用开销。
 *
 * <p>判定链（详见 {@link AttackSourceClassifier}）：
 * <ul>
 *   <li>玩家直接攻击 / 玩家投射物（getEntity 已解析为 owner）→ 触发</li>
 *   <li>玩家宠物（owner 为玩家）→ 触发</li>
 *   <li>玩家点燃的 TNT（owner 为玩家）→ 触发</li>
 *   <li>铁傀儡 / 村民卫兵 / 怪物内斗 / 环境伤害 → 不介入，走原版逻辑</li>
 * </ul>
 *
 * <p>⚠️ 用户两次强调的硬约束，实现后必须逐条真机验证（9 种伤害源）。
 */
@Mixin(LivingEntity.class)
public abstract class LivingEntityHurtMixin {

    @Inject(method = "hurt", at = @At("HEAD"))
    private void peaceandlove$onHurt(DamageSource source, float amount,
                                     CallbackInfoReturnable<Boolean> cir) {
        Object self = this;
        if (!(self instanceof Mob mob)) {
            return;
        }
        // 快速路径：不在适配范围直接返回
        if (!NeutralizationScope.isNeutralized(mob.getType(), PeaceAndLove.config().get())) {
            return;
        }
        // 唯一触发条件：伤害源可归因到玩家（含投射物/宠物/TNT 溯源）
        Player attacker = AttackSourceClassifier.resolveAttackingPlayer(source);
        if (attacker != null) {
            AngerController.onPlayerAttack(mob, attacker);
        }
        // 其余伤害源 → 完全不介入，走原版逻辑
    }
}
