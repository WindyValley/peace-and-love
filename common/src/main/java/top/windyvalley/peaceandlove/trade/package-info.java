/**
 * 交易系统。
 *
 * <p>为被中立化的生物提供原版 Merchant 交易能力。

<p>实现方式：通过 Mixin 向 {@code Mob} 基类注入原版 {@code Merchant}
接口（详见 ADR-002），复用整套原版交易 GUI 与网络协议，
不自建 Menu、不写自定义数据包。

<p>补货策略：{@code MerchantOffer.maxUses = 1} + 自实现的每游戏日
{@code resetAllUses()}。**不使用** {@code Villager.restock()} ——
那会连带引入 gossip / demand 等副作用（详见 ADR-003）。
 *
 * <p><b>依赖：</b>scope, pricing, config
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.trade;
