package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import top.windyvalley.peaceandlove.ProbeResults;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * P1 探针 —— 验证 hurt() 注入点在双端可用。
 *
 * 实测签名（1.21.1 mappings）：
 *     boolean hurt(net.minecraft.world.damagesource.DamageSource, float)   -> a
 *
 * 本模组的仇恨语义（ADR-004 决策三）：
 *     仅当 source.getEntity() instanceof Player 时才介入，
 *     NPC 攻击/环境伤害一律放行走原版逻辑。
 */
@Mixin(LivingEntity.class)
public abstract class LivingEntityHurtProbeMixin {

    @Inject(method = "hurt", at = @At("HEAD"))
    private void pal$probeHurt(DamageSource source, float amount,
                               CallbackInfoReturnable<Boolean> cir) {
        Object self = this;
        if (!(self instanceof Mob mob)) {
            return;
        }
        // getEntity() 会自动解析投射物的 owner（射箭的玩家）
        if (source.getEntity() instanceof Player player) {
            ProbeResults.recordPlayerAttack(mob, player);
        }
    }
}
