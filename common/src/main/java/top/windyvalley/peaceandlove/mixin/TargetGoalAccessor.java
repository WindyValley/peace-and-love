package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.target.TargetGoal;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * TargetGoal 字段访问器。
 *
 * <p>{@code TargetGoal.mob} 为 {@code protected final Mob}（注意构造收
 * PathfinderMob，但字段存为 Mob）。同族示警 Mixin 需要从 goal 实例反查
 * 持有者，普通代码不在 net.minecraft 包内、也非子类，必须经 Accessor。
 *
 * <p>Mixin 包内类不得被普通代码直接引用（IllegalClassLoadError），
 * 仅同包 Mixin/Accessor 间互转。
 */
@Mixin(TargetGoal.class)
public interface TargetGoalAccessor {

    @Accessor("mob")
    Mob peaceandlove$getMob();
}
