/**
 * Mixin 注入。
 *
 * <p>所有 Mixin 类的唯一存放位置，是依赖链的最上层。

<p><b>纪律：本包内的类不得被普通代码直接引用</b> ——
Mixin 类由 Mixin 框架在类加载期处理，普通代码引用会抛
{@code IllegalClassLoadError: ... cannot be referenced directly}。

<p>工具类、结果收集器等辅助代码必须放在本包**之外**。
这个坑在 P1 验证阶段实际踩过一次。

<p>每新增一个 Mixin，必须同步在
{@code peaceandlove-common.mixins.json} 的 mixins 数组中登记。
 *
 * <p><b>依赖：</b>trade, neutralize, anger（最上层）
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.mixin;
