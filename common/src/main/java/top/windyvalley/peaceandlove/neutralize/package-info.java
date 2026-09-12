/**
 * 生物中立化。
 *
 * <p>移除敌对生物的主动索敌行为，使其默认不攻击玩家。

<p>双策略（详见 ADR-004）：
<ul>
  <li><b>Goal 系</b>（32 种）—— 通过 {@code GoalSelector.removeAllGoals(Predicate)}
      移除 {@code NearestAttackableTargetGoal} 等主动索敌 Goal</li>
  <li><b>Brain 系</b>（6 种）—— 拦截 Brain 的 activity 更新</li>
</ul>

<p>特殊适配 10 种，其中末影人的凝视激怒、僵尸猪灵的群体报复
需单独处理（P4 验证发现，详见 docs/P1-P4-VERIFY.md）。

<p>白名单热重载时通过 WrappedGoal 快照恢复原始 Goal。
 *
 * <p><b>依赖：</b>scope, config
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.neutralize;
