package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * Mob 字段访问器。
 *
 * <p><b>实测依据</b>（check_mob_fields.py 字节码验证）：
 * {@code Mob.goalSelector} 与 {@code Mob.targetSelector} 均为
 * <b>protected final</b>。本模组代码既不在 {@code net.minecraft.world.entity}
 * 包、也不是 Mob 子类，无法直接访问，必须经 Accessor Mixin。
 *
 * <p>final 不影响读取，只影响赋值 —— 我们只读不写，OK。
 *
 * <p><b>⚠️ Mixin 类加载约束</b>（踩过的坑，见 memory）：mixin 包内的类
 * 不能被普通代码直接引用，否则运行时 {@code IllegalClassLoadError}。
 * 因此普通代码一律经由 {@code neutralize/MobAccess} 门面访问，
 * 不得直接 import 本接口。
 */
@Mixin(Mob.class)
public interface MobAccessor {

    @Accessor("goalSelector")
    GoalSelector peaceandlove$goalSelector();

    @Accessor("targetSelector")
    GoalSelector peaceandlove$targetSelector();
}
