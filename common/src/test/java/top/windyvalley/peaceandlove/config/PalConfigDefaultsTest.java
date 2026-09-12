package top.windyvalley.peaceandlove.config;

import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 配置默认值测试。
 *
 * <p>这几条断言对应设计阶段反复纠正过的点，每一条都有据可查，
 * 不是随手写的。改动默认值前请先读 {@code docs/02-design.md} §6
 * 和 {@code docs/adr/004}。
 */
class PalConfigDefaultsTest {

    private final PalConfig cfg = PalConfig.defaults();

    @Test
    void 默认白名单恰好6项() {
        assertEquals(6, cfg.hostile_whitelist().size(),
                "默认白名单必须恰好 6 项：掠夺者/卫道士/唤魔者/恼鬼/幻翼/潜影贝");
    }

    @Test
    void 默认白名单内容() {
        Set<String> wl = cfg.whitelistSet();
        assertTrue(wl.contains("minecraft:pillager"),   "掠夺者");
        assertTrue(wl.contains("minecraft:vindicator"), "卫道士");
        assertTrue(wl.contains("minecraft:evoker"),     "唤魔者");
        assertTrue(wl.contains("minecraft:vex"),        "恼鬼");
        assertTrue(wl.contains("minecraft:phantom"),    "幻翼");
        assertTrue(wl.contains("minecraft:shulker"),    "潜影贝");
    }

    @Test
    void 凋灵不在默认白名单() {
        // 凋灵已适配，默认被中立化（boss_trading_enabled=false 时不开交易），
        // 因此不占白名单位。这是 ADR-004 的最终决策，曾反复纠正。
        assertFalse(cfg.whitelistSet().contains("minecraft:wither"),
                "凋灵不在默认白名单 —— 它默认被中立化");
    }

    @Test
    void 监守者不在默认白名单() {
        assertFalse(cfg.whitelistSet().contains("minecraft:warden"),
                "监守者不在默认白名单 —— 同凋灵，默认被中立化");
    }

    @Test
    void 末影龙不在默认白名单() {
        // 末影龙 v1.0 根本不适配，行为完全不变，不占白名单位。
        assertFalse(cfg.whitelistSet().contains("minecraft:ender_dragon"),
                "末影龙不适配，不应出现在白名单");
    }

    @Test
    void 交易默认开关() {
        assertTrue(cfg.trading_enabled(), "trading_enabled 默认 true");
        assertFalse(cfg.boss_trading_enabled(), "boss_trading_enabled 默认 false");
    }

    @Test
    void 定价参数() {
        assertEquals(128, cfg.price_max(), "price_max = 128（双输入槽上限）");
        assertEquals(2.0, cfg.epk_cheap(), 1e-9, "epk_cheap = 2.0");
        assertEquals(0.005, cfg.epk_rare(), 1e-9, "epk_rare = 0.005");
    }

    @Test
    void 补货与限购() {
        assertEquals(1, cfg.max_uses_per_day(), "max_uses_per_day = 1");
        assertEquals(1, cfg.restock_interval_days(), "restock_interval_days = 1");
    }

    @Test
    void 仇恨参数() {
        assertEquals(30, cfg.anger_cooldown_seconds(), "anger_cooldown_seconds = 30");
        assertEquals(4.0, cfg.kin_alert_radius(), 1e-9, "kin_alert_radius = 4.0");
        assertEquals(32.0, cfg.anger_cooldown_distance(), 1e-9,
                "anger_cooldown_distance = 32.0");
    }
}
