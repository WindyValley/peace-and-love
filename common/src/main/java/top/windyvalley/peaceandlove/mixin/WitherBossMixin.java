package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.entity.boss.wither.WitherBoss;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 凋灵侧头的硬编码攻击拦截 —— T-NEUT-006。
 *
 * <p>通用 {@code GoalBasedStrategy} 已删掉凋灵 targetSelector 里的主头索敌
 * （{@code NearestAttackableTargetGoal}），并保留 {@code HurtByTargetGoal} 受击反击。
 * 但两个侧头（head 1/2）的攻击<b>完全绕过 GoalSelector</b>，在
 * {@code WitherBoss#customServerAiStep()} 里有两条硬编码路径：
 * <ol>
 *   <li>每 tick {@code getNearbyEntities} 随机选目标 → {@code setAlternativeTarget}
 *       → 次 tick 对锁定目标 {@code performRangedAttack(i+1, target)}；</li>
 *   <li>锁定不到时，{@code idleHeadUpdates} 计数满后朝随机坐标
 *       {@code performRangedAttack(i+1, x,y,z,true)} 无差别乱射。</li>
 * </ol>
 *
 * <p><b>唯一开火出口</b>：三条发射路径（主头 RangedAttackGoal 回调、侧头锁定、
 * 侧头乱射）最终都调用私有的 {@code performRangedAttack(int head, double x,y,z,
 * boolean dangerous)}（{@code new WitherSkull + addFreshEntity} 只在此方法内）。
 * 在它 HEAD 对 head≥1 且中立化者取消，即同时挡住侧头的锁定攻击与 idle 乱射。
 * 不选拦 {@code setAlternativeTarget}：idle 乱射不依赖锁定目标，单拦它挡不住乱射。
 *
 * <ul>
 *   <li><b>主头 head 0 放行</b> —— 由 RangedAttackGoal 经公共
 *       {@code performRangedAttack(target,power)→performRangedAttack(0,...)} 触发，
 *       该 goal 需 {@code getTarget()}：中立无目标不发射，玩家攻击后经保留的
 *       HurtByTargetGoal 设目标、主头照常反击。</li>
 *   <li>侧头仍可能因 alt 目标转动头部（纯视觉）；头颅不再生成、无伤害。</li>
 *   <li>召唤爆炸（invulnerableTicks 分支的 level().explode）与飞行破坏方块是
 *       独立路径，不经过本方法，保持原版。</li>
 * </ul>
 *
 * <p>未中立化（白名单内）时直接放行，100% 原版凋灵战。
 */
@Mixin(WitherBoss.class)
public abstract class WitherBossMixin {

    @Inject(
            method = "performRangedAttack(IDDDZ)V",
            at = @At("HEAD"),
            cancellable = true
    )
    private void peaceandlove$blockSideHeadSkulls(int head, double x, double y, double z,
                                                  boolean dangerous, CallbackInfo ci) {
        WitherBoss wither = (WitherBoss) (Object) this;
        // 主头 0 保留（中立不触发、受击反击走它）；只拦截两个侧头 1/2 的硬编码发射
        if (head <= 0) {
            return;
        }
        if (NeutralizationScope.isNeutralized(wither.getType(), PeaceAndLove.config().get())) {
            ci.cancel();
        }
    }
}
