package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import top.windyvalley.peaceandlove.mixin.HurtByTargetGoalAccessor;
import top.windyvalley.peaceandlove.mixin.MobAccessor;

/**
 * Mob 字段/Goal 访问门面。
 *
 * <p>存在的唯一原因：Accessor Mixin 在 mixin 包内，普通代码直接引用会触发
 * Mixin 类加载约束（{@code IllegalClassLoadError}）。普通代码一律经由本门面
 * 间接访问 Mob 的 goal/target selector 与 HurtByTargetGoal 内部字段。
 *
 * <p>字段访问性已由 check_mob_fields.py 字节码验证为 protected/private，
 * 故必须经 Accessor，不能直接访问。
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

    /**
     * 打开/关闭一个 HurtByTargetGoal 的同族示警开关（{@code alertSameType}）。
     *
     * <p>用于 B 类怪物（骷髅/蜘蛛等，原生有 HurtBy 但未开示警）：中立化时
     * 置 true 使其进入 alertOthers 路径，白名单回滚时置回 false。
     *
     * @return 传入 goal 确为 HurtByTargetGoal 返回 true；否则 false（不处理）
     */
    public static boolean setAlertSameType(Goal goal, boolean value) {
        if (goal instanceof HurtByTargetGoal hurtBy) {
            ((HurtByTargetGoalAccessor) hurtBy).peaceandlove$setAlertSameType(value);
            return true;
        }
        return false;
    }
}
