package top.windyvalley.peaceandlove.config;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 模组配置数据类。
 *
 * <p>字段名与配置文件 JSON key **完全一致**，便于序列化（详见
 * {@code docs/02-design.md} §6）。
 *
 * <p>使用 record 保证不可变 —— 配置热重载时是整体替换实例，
 * 而不是原地改字段，避免读到「一半新一半旧」的中间态。
 *
 * <p><b>默认白名单的语义必须讲清楚</b>（这是设计阶段被纠正过的点）：
 * 白名单 = 「已适配但保持原版敌对行为」。它不等于「不适配」。
 * 凋灵与监守者<b>不在</b>默认白名单 —— 它们已适配，默认被中立化，
 * 只是 {@code boss_trading_enabled=false} 时不开交易。
 * 末影龙<b>也不在</b> —— 它根本没适配（v1.1 才做），行为完全不变，
 * 不占白名单位。
 */
public record PalConfig(
        // ── 生效范围 ──
        /** 已适配但保持原版敌对行为的生物。默认恰好 6 项。 */
        List<String> hostile_whitelist,

        // ── 仇恨 ──
        /** 同族示警半径（球形），仅玩家攻击触发。 */
        double kin_alert_radius,
        /** 脱战冷却秒数，0 = 永久敌对。 */
        int anger_cooldown_seconds,
        /** 脱战距离（格）。 */
        double anger_cooldown_distance,

        // ── 交易 ──
        /** 全局交易开关。 */
        boolean trading_enabled,
        /** Boss（凋灵/监守者）中立化但默认不开交易。 */
        boolean boss_trading_enabled,
        /** MerchantOffer.maxUses，每日每样限购次数。 */
        int max_uses_per_day,
        /** 补货间隔（游戏日），1=每天，3=三天一次。 */
        int restock_interval_days,

        // ── 定价 ──
        /** 价格上限，源于 MerchantOffer 双输入槽 64+64。 */
        int price_max,
        /** 廉价锚点 epk。 */
        double epk_cheap,
        /** 稀有锚点 epk。 */
        double epk_rare,
        /** 手工修正，key = "实体ID/物品ID"，value = 价格。 */
        Map<String, Integer> price_overrides
) {

    /** 默认白名单 —— 恰好 6 项，勿随意增减。 */
    public static final List<String> DEFAULT_WHITELIST = List.of(
            "minecraft:pillager",
            "minecraft:vindicator",
            "minecraft:evoker",
            "minecraft:vex",
            "minecraft:phantom",
            "minecraft:shulker"
    );

    /** 一份完整的默认配置。 */
    public static PalConfig defaults() {
        return new PalConfig(
                DEFAULT_WHITELIST,
                4.0,      // kin_alert_radius
                30,       // anger_cooldown_seconds
                32.0,     // anger_cooldown_distance
                true,     // trading_enabled
                false,    // boss_trading_enabled
                1,        // max_uses_per_day
                1,        // restock_interval_days
                128,      // price_max
                2.0,      // epk_cheap
                0.005,    // epk_rare
                Map.of()  // price_overrides
        );
    }

    /** 白名单转 Set，便于 O(1) 门控判定。 */
    public Set<String> whitelistSet() {
        return Set.copyOf(hostile_whitelist);
    }

    /**
     * 返回一个仅白名单不同的新实例（不可变拷贝）。
     *
     * <p>record 不可变，白名单变更走「整体替换」而非原地修改，
     * 配合 {@code ConfigManager} 的 volatile 引用保证热重载线程安全。
     */
    public PalConfig withWhitelist(List<String> newWhitelist) {
        return new PalConfig(
                newWhitelist,
                kin_alert_radius, anger_cooldown_seconds, anger_cooldown_distance,
                trading_enabled, boss_trading_enabled, max_uses_per_day, restock_interval_days,
                price_max, epk_cheap, epk_rare, price_overrides);
    }
}
