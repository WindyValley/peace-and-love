package top.windyvalley.peaceandlove.pricing;

import org.junit.jupiter.api.Test;
import top.windyvalley.peaceandlove.config.PalConfig;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link ConfigurablePriceCurve} 配置绑定层单测（T-PRICE-002.2）。
 *
 * <p>验证三件事：①默认配置下结果等于直接调用纯函数 {@link PricingEngine}；
 * ②改锚点/上限即时改变价格，等价于「热重载后新配置生效」（不缓存参数）；
 * ③绕过 loader 的畸形配置被明确拒绝（纵深防御）。纯 Java，无 MC 依赖。
 */
class ConfigurablePriceCurveTest {

    /** 复制默认配置，仅覆盖定价三参数。 */
    private static PalConfig cfg(double cheap, double rare, int max) {
        PalConfig d = PalConfig.defaults();
        return new PalConfig(
                d.hostile_whitelist(),
                d.kin_alert_radius(), d.anger_cooldown_seconds(), d.anger_cooldown_distance(),
                d.trading_enabled(), d.boss_trading_enabled(),
                d.max_uses_per_day(), d.restock_interval_days(),
                max, cheap, rare, d.price_overrides());
    }

    // ── 默认参数：与纯函数完全一致 ──

    @Test
    void 默认锚点_与PricingEngine直接计算一致() {
        PalConfig d = PalConfig.defaults(); // cheap=2.0 rare=0.005 max=128
        for (double epk : new double[]{0.0, 0.005, 0.05, 0.5, 2.0, 6.0, 0.0083}) {
            assertEquals(
                    PricingEngine.price(epk, d.epk_cheap(), d.epk_rare(), d.price_max()),
                    ConfigurablePriceCurve.price(epk, d),
                    "epk=" + epk);
        }
    }

    @Test
    void 默认锚点端到端_廉价1_稀有128() {
        PalConfig d = PalConfig.defaults();
        assertEquals(1, ConfigurablePriceCurve.price(2.0, d));
        assertEquals(128, ConfigurablePriceCurve.price(0.005, d));
    }

    // ── 改锚点即时生效（热重载语义）──

    @Test
    void 调紧稀有锚点_中间稀有物变得更贵() {
        // 固定一个中间 epk，把 rare 从 0.005 调大到 0.05（更接近 cheap），
        // 曲线在该区间被压陡，0.05 处直接撞上稀有锚点 → 更贵
        double epk = 0.05;
        int before = ConfigurablePriceCurve.price(epk, cfg(2.0, 0.005, 128));
        int after = ConfigurablePriceCurve.price(epk, cfg(2.0, 0.05, 128));
        assertEquals(128, after, "epk 恰好等于新稀有锚点应给最高价");
        assertTrue(after > before, "调紧稀有锚点应使该物更贵：" + before + " -> " + after);
    }

    @Test
    void 同一epk换配置实例_价格随之变化_模拟热重载不缓存() {
        double epk = 0.3;
        int loose = ConfigurablePriceCurve.price(epk, cfg(4.0, 0.005, 128));  // cheap 抬高
        int tight = ConfigurablePriceCurve.price(epk, cfg(2.0, 0.005, 128));
        assertNotEquals(loose, tight, "更换配置实例必须即时反映，不得缓存旧锚点");
    }

    @Test
    void 自定义price_max生效() {
        PalConfig d = cfg(2.0, 0.005, 32);
        assertEquals(32, ConfigurablePriceCurve.price(0.001, d), "稀有端钳到自定义上限 32");
        assertEquals(1, ConfigurablePriceCurve.price(2.0, d), "廉价端仍为 1");
    }

    // ── 非法配置：纵深防御 ──

    @Test
    void null配置_抛出而非静默给价() {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> ConfigurablePriceCurve.price(1.0, null));
        assertTrue(e.getMessage().contains("配置未初始化"), e.getMessage());
    }

    @Test
    void cheap不大于rare_抛出并指出锚点名() {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> ConfigurablePriceCurve.price(1.0, cfg(0.005, 2.0, 128)));
        String msg = e.getMessage();
        assertTrue(msg.contains("epk_cheap"), msg);
        assertTrue(msg.contains("epk_rare"), msg);
        assertTrue(msg.contains("reload"), "应提示管理员 reload：" + msg);
    }

    @Test
    void 锚点相等_视为非法() {
        assertThrows(IllegalArgumentException.class,
                () -> ConfigurablePriceCurve.price(1.0, cfg(1.0, 1.0, 128)));
    }

    @Test
    void 非正锚点_拒绝() {
        assertThrows(IllegalArgumentException.class,
                () -> ConfigurablePriceCurve.price(1.0, cfg(0.0, 0.005, 128)));
        assertThrows(IllegalArgumentException.class,
                () -> ConfigurablePriceCurve.price(1.0, cfg(2.0, -0.01, 128)));
    }

    @Test
    void price_max小于1_拒绝() {
        assertThrows(IllegalArgumentException.class,
                () -> ConfigurablePriceCurve.price(1.0, cfg(2.0, 0.005, 0)));
    }
}
