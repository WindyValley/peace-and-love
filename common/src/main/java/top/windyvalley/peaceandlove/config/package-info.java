/**
 * 配置系统。
 *
 * <p>加载与热重载模组配置，是整个依赖链的最底层。

<p>本包**不依赖任何其他业务包**。配置项包括：白名单、交易开关、
仇恨参数（脱战时长、示警半径）、定价上限等。

<p>白名单支持运行时热重载 —— 修改后无需重启服务端，
通过 {@code /peaceandlove reload} 立即生效。
 *
 * <p><b>依赖：</b>无（最底层）
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.config;
