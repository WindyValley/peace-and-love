package top.windyvalley.peaceandlove.pricing;

import top.windyvalley.peaceandlove.config.PalConfig;

/**
 * 定价曲线的配置绑定层 —— 从 {@link PalConfig} 读锚点与上限，算出某掉落物的绿宝石价。
 *
 * <p>这是<b>定价曲线读配置的唯一入口</b>（T-PRICE-002.2）：交易报价组装、定价表构建
 * 一律走这里，不得自行 new 曲线或缓存参数。本类无状态，每次调用都从传入的
 * {@link PalConfig} 即时读取 —— 配置整体不可变、由 ConfigManager 在热重载时替换实例，
 * 因此 {@code /pal reload} 改锚点后，下一次定价立即生效。
 *
 * <p>纯数学（对数曲线、锚点映射）仍在 {@link PricingEngine}（无配置、可独立测试）；
 * 本类只负责「取配置 → 校验 → 委托」，职责分开：
 * <ul>
 *   <li>{@link PricingEngine}：给定 epk 和三个数，怎么算价</li>
 *   <li>本类：这三个数从当前配置的哪里来、是否合法</li>
 * </ul>
 *
 * <p>正常运行不会抛参数异常 —— {@code ConfigLoader} 已对锚点做范围 clamp。
 * 这里再校验一次是<b>纵深防御</b>：配置来源不止文件（测试、未来的 API/数据包），
 * 一旦绕过 loader 给出畸形配置，要抛出明确错误而不是算出卖 0 绿宝石之类的脏价格。
 */
public final class ConfigurablePriceCurve {

    private ConfigurablePriceCurve() {
    }

    /**
     * 按当前配置计算单个掉落物的绿宝石价。
     *
     * @param epk    期望每次击杀产出量（玩家击杀 + looting 0 基准）
     * @param config 当前生效配置（不得为 null）
     * @return 绿宝石价，已 clamp 到 [1, price_max]
     * @throws IllegalArgumentException 配置缺失或锚点关系非法时（提示管理员修正配置）
     */
    public static int price(double epk, PalConfig config) {
        if (config == null) {
            throw new IllegalArgumentException("定价失败：配置未初始化（PalConfig 为 null）");
        }
        double cheap = config.epk_cheap();
        double rare = config.epk_rare();
        int max = config.price_max();

        // loader 已保证 cheap > rare > 0、max >= 1；此处兜底，防止绕过 loader 的畸形配置
        if (!(cheap > 0d && rare > 0d) || cheap <= rare) {
            throw new IllegalArgumentException(
                    "定价锚点配置非法：要求 epk_cheap > epk_rare > 0，"
                            + "当前 epk_cheap=" + cheap + "、epk_rare=" + rare
                            + "。请修正 peaceandlove.json 后执行 /pal reload。");
        }
        if (max < 1) {
            throw new IllegalArgumentException(
                    "定价上限配置非法：price_max=" + max + " 必须 >= 1。");
        }
        return PricingEngine.price(epk, cheap, rare, max);
    }
}
