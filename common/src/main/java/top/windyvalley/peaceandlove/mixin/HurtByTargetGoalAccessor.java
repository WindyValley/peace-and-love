package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * HurtByTargetGoal 字段访问器。
 *
 * <p>{@code alertSameType} 是 private boolean（非 final），默认 false。只有构造后
 * 调用 {@code setAlertOthers(...)} 才置 true（A 类原生调用，B 类没有）。中立化
 * B 类怪物（骷髅/蜘蛛/苦力怕/女巫/末影人/凋灵）时经本 accessor 打开该字段，
 * 使其进入 alertOthers 路径；白名单回滚时写回 false。
 */
@Mixin(HurtByTargetGoal.class)
public interface HurtByTargetGoalAccessor {

    @Accessor("alertSameType")
    void peaceandlove$setAlertSameType(boolean value);

    @Accessor("alertSameType")
    boolean peaceandlove$isAlertSameType();
}
