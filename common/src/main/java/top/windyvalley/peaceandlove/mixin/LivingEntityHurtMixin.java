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
 * 仇恨触发点 —— T-ANGER-001。在受伤事件注入，
 * <b>只在玩家归因时</b>追加玩家专属仇恨与同族示警。
 *
 * <p>这不改变生物之间的正常反击：任何伤害源仍走原版逻辑，
 * 本 mixin 只在攻击者是玩家时额外调用 {@link AngerController#onPlayerAttack}。
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
        // 只有玩家归因的伤害才追加玩家专属仇恨与同族示警；
        // 其他伤害源不干预，继续走原版反击链。
        Player attacker = AttackSourceClassifier.resolveAttackingPlayer(source);
        if (attacker != null) {
            AngerController.onPlayerAttack(mob, attacker);
        }
    }
}
