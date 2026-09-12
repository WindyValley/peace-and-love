/**
 * 仇恨管理。
 *
 * <p>管理被中立化生物受攻击后的反击行为。

<p>三条硬约束：
<ol>
  <li><b>仅玩家攻击触发</b> —— 铁傀儡、村民卫兵、怪物内斗、
      环境伤害一律不介入。玩家的投射物、TNT、owner 为玩家的宠物视同玩家攻击</li>
  <li><b>仇恨锁定攻击者本人</b> —— 按 UUID 单目标锁定，
      玩家 A 动手不会牵连旁边的玩家 B</li>
  <li><b>同族示警不链式扩散</b> —— 4 格球形内同 EntityType 的生物被通知，
      但被通知者不再向外传播</li>
</ol>

<p>脱战条件：30 秒无交互 或 距离超过 32 格，恢复中立。
 *
 * <p><b>依赖：</b>scope, config
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.anger;
