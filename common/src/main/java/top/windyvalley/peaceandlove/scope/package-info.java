/**
 * 生效范围判定。
 *
 * <p>决定一个生物是否应当被中立化，是全模组的**判定枢纽**。

<p>核心规则（双重门控）：
<pre>
被中立化 = 在已适配列表中 AND 不在白名单中
</pre>

<p>「已适配列表」是代码能力边界（v1.0 共 38 种，编译期常量），
「白名单」是运行时配置。两者语义不同，不可混为一谈：
第三方 Mod 的生物天然不在已适配列表内，因此完全不受影响 ——
这不是靠白名单实现的。

<p><b>本包不得依赖 trade / neutralize / anger</b>，否则形成循环依赖。
 *
 * <p><b>依赖：</b>config
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.scope;
