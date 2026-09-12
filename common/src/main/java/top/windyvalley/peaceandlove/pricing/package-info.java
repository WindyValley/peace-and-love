/**
 * 定价系统。
 *
 * <p>把掉落物的「每击杀期望产出」(epk) 映射为绿宝石价格。

<p>采用对数曲线：
<pre>
pos   = log(2 / epk) / log(400)
price = clamp(1 + 127 × pos, 1, 128)
</pre>

<p>上限 128 源于 {@code MerchantOffer} 的双输入槽设计限制。
110 个掉落物条目经实测全部单调、无一撞顶。

<p>本包**独立于中立化与交易逻辑**，仅依赖 config 读取定价参数，
因此可独立测试与并行开发。
 *
 * <p><b>依赖：</b>config
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.pricing;
