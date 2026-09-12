package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import top.windyvalley.peaceandlove.mixin.MobAccessor;

/**
 * Mob 字段访问门面。
 *
 * <p>存在的唯一原因：{@link MobAccessor} 在 mixin 包内，普通代码直接
 * 引用会触发 Mixin 类加载约束（{@code IllegalClassLoadError}）。普通代码
 * 一律经由本门面间接访问 Mob 的 goal/target selector。
 *
 * <p>字段访问性已由 check_mob_fields.py 字节码验证为 protected final，
 * 故必须经 Accessor，不能直接 mob.goalSelector。
 */
public final class MobAccess {

    private MobAccess() {
    }

    /** 主动索敌/行为 Goal 选择器。 */
    public static GoalSelector goalSelectorOf(Mob mob) {
        return ((MobAccessor) mob).peaceandlove$goalSelector();
    }

    /** 目标选择 Goal 选择器（中立化主要操作对象）。 */
    public static GoalSelector targetSelectorOf(Mob mob) {
        return ((MobAccessor) mob).peaceandlove$targetSelector();
    }
}
