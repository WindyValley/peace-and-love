package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import net.minecraft.world.entity.ai.goal.WrappedGoal;

import java.util.ArrayList;
import java.util.List;

/**
 * Goal 快照 —— 记录中立化时被移除的 Goal，供可逆还原。
 *
 * <p>中立化是可逆操作：白名单热重载时，生物要从「中立」恢复回「原版敌对」。
 * 实现方式是移除前先把 (priority, goal) 快照下来，restore 时原样塞回。
 *
 * <p><b>实测依据</b>（spike 验证）：{@code WrappedGoal.getGoal()} 与
 * {@code getPriority()} 均为 public，因此快照无需反射。
 *
 * @param priority 该 Goal 在原 GoalSelector 中的优先级
 * @param goal     被移除的 Goal 实例（保持引用，restore 时塞回同一个对象）
 */
public record GoalSnapshot(int priority, Goal goal) {

    /**
     * 从一个 GoalSelector 中捕获指定 Goal 的快照（按谓词过滤）。
     *
     * <p>遍历 {@code selector.getAvailableGoals()}（public），
     * 对每个命中的 WrappedGoal 取其 (priority, goal)。
     */
    public static List<GoalSnapshot> capture(GoalSelector selector,
                                             java.util.function.Predicate<Goal> filter) {
        List<GoalSnapshot> out = new ArrayList<>();
        for (WrappedGoal wrapped : selector.getAvailableGoals()) {
            Goal g = wrapped.getGoal();
            if (filter.test(g)) {
                out.add(new GoalSnapshot(wrapped.getPriority(), g));
            }
        }
        return out;
    }

    /**
     * 把快照原样塞回 GoalSelector。
     *
     * <p>注意：只负责 add，不处理「是否已存在」——调用方须保证
     * 同一个 Goal 不会被 add 两次（重复 add 会触发 GoalSelector 内部断言）。
     */
    public static void restore(GoalSelector selector, List<GoalSnapshot> snapshots) {
        for (GoalSnapshot s : snapshots) {
            selector.addGoal(s.priority(), s.goal());
        }
    }

    /** 便捷入口：直接对一只 Mob 的 targetSelector 做快照。 */
    public static List<GoalSnapshot> captureTargetGoals(Mob mob,
                                                        java.util.function.Predicate<Goal> filter) {
        return capture(MobAccess.targetSelectorOf(mob), filter);
    }
}
