package top.windyvalley.peaceandlove.mixin;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.Brain;
import net.minecraft.world.entity.ai.memory.ExpirableValue;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import top.windyvalley.peaceandlove.neutralize.BrainAttackGate;
import top.windyvalley.peaceandlove.neutralize.BrainOwners;

import java.util.Optional;

/**
 * Brain 系中立化的源头拦截 —— 取代旧的「每 tick 全服擦攻击记忆」。
 *
 * <p>字节码实测：所有记忆写入（传感器、行为、被打反击、同伴广播）最终都
 * 汇聚到包私有方法 {@code setMemoryInternal}，没有绕过它的旁路。在它开头
 * 按门控取消攻击类记忆的写入，等于从源头拒绝，一次拦截覆盖全部来源。
 *
 * <p>两个注入点：
 * <ul>
 *   <li>{@code tick} HEAD：tick 的参数直接带着主人实体，顺手登记到
 *       {@link BrainOwners}（Brain 对象自身不持有实体引用）；</li>
 *   <li>{@code setMemoryInternal} HEAD：查到主人后交给
 *       {@link BrainAttackGate} 判断这次攻击记忆写入是否取消。</li>
 * </ul>
 *
 * <p><b>清空一律放行</b>：{@code eraseMemory} 也走本方法，但携带空值。
 * 只拦截「真正写入一个目标」，否则过期/失效目标的正常清除也会被挡，
 * 造成残留。
 */
@Mixin(Brain.class)
public abstract class BrainMixin {

    @Inject(method = "tick", at = @At("HEAD"))
    private void peaceandlove$registerOwner(ServerLevel level, LivingEntity owner,
                                            CallbackInfo ci) {
        BrainOwners.set((Brain<?>) (Object) this, owner);
    }

    @Inject(method = "setMemoryInternal", at = @At("HEAD"), cancellable = true)
    private void peaceandlove$blockAttackMemory(
            MemoryModuleType<?> memoryType,
            Optional<? extends ExpirableValue<?>> value,
            CallbackInfo ci) {
        // 清空（eraseMemory 传入空 Optional）放行：不挡正常的记忆清除
        if (value == null || value.isEmpty()) {
            return;
        }
        LivingEntity owner = BrainOwners.get((Brain<?>) (Object) this);
        if (owner == null) {
            return;
        }
        if (BrainAttackGate.shouldBlock(owner, memoryType)) {
            ci.cancel();
        }
    }
}
