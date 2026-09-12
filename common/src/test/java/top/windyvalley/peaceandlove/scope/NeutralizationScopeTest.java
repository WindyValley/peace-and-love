package top.windyvalley.peaceandlove.scope;

import net.minecraft.world.entity.EntityType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import top.windyvalley.peaceandlove.config.PalConfig;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 双重决策门控测试 —— 全项目最关键的判定。
 *
 * <p>真值表（docs/tasks/T-SCOPE-002）：
 * <pre>
 * 已适配 | 在白名单 | isNeutralized
 *   ✅   |   ❌    | true
 *   ✅   |   ✅    | false
 *   ❌   |   ❌    | false
 *   ❌   |   ✅    | false（配置无效）
 * </pre>
 *
 * <p>引用 EntityType 需注册表 bootstrap（见 AdaptedMobsTest）。
 */
class NeutralizationScopeTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    /** 构造一个只含指定白名单的配置，其余用默认值。 */
    private PalConfig cfg(List<String> whitelist) {
        PalConfig d = PalConfig.defaults();
        return new PalConfig(
                whitelist,
                d.kin_alert_radius(), d.anger_cooldown_seconds(), d.anger_cooldown_distance(),
                d.trading_enabled(), d.boss_trading_enabled(),
                d.max_uses_per_day(), d.restock_interval_days(),
                d.price_max(), d.epk_cheap(), d.epk_rare(), d.price_overrides());
    }

    // ── isNeutralized 真值表 ──

    @Test
    void 已适配且不在白名单_中立化() {
        // zombie：已适配，默认白名单不含 → true
        assertTrue(NeutralizationScope.isNeutralized(EntityType.ZOMBIE, PalConfig.defaults()));
    }

    @Test
    void 已适配但在白名单_保持原版() {
        // pillager：已适配，默认白名单含 → false
        assertFalse(NeutralizationScope.isNeutralized(EntityType.PILLAGER, PalConfig.defaults()));
    }

    @Test
    void 未适配且不在白名单_保持原版() {
        // cow：未适配 → false（与是否白名单无关）
        assertFalse(NeutralizationScope.isNeutralized(EntityType.COW, PalConfig.defaults()));
    }

    @Test
    void 未适配但在白名单_配置无效仍保持原版() {
        // 把 cow（未适配）放进白名单 → 仍 false
        PalConfig c = cfg(List.of("minecraft:cow"));
        assertFalse(NeutralizationScope.isNeutralized(EntityType.COW, c),
                "未适配生物即使列入白名单也不会被中立化");
    }

    @Test
    void 白名单变更立即生效() {
        // 同一生物，不同配置实例 → 结果不同（证明读当前值不缓存）
        assertTrue(NeutralizationScope.isNeutralized(EntityType.ZOMBIE, cfg(List.of())));
        assertFalse(NeutralizationScope.isNeutralized(EntityType.ZOMBIE,
                cfg(List.of("minecraft:zombie"))));
    }

    // ── canTrade ──

    @Test
    void 普通生物默认可交易() {
        assertTrue(NeutralizationScope.canTrade(EntityType.ZOMBIE, PalConfig.defaults()));
    }

    @Test
    void Boss默认不可交易但已中立化() {
        // 凋灵：已适配、不在白名单 → 中立化 true；但 boss_trading_enabled=false → 交易 false
        assertTrue(NeutralizationScope.isNeutralized(EntityType.WITHER, PalConfig.defaults()),
                "凋灵默认被中立化");
        assertFalse(NeutralizationScope.canTrade(EntityType.WITHER, PalConfig.defaults()),
                "boss_trading_enabled=false 时凋灵不开交易");
    }

    @Test
    void Boss开启交易开关后可交易() {
        PalConfig d = PalConfig.defaults();
        PalConfig c = new PalConfig(
                d.hostile_whitelist(), d.kin_alert_radius(),
                d.anger_cooldown_seconds(), d.anger_cooldown_distance(),
                d.trading_enabled(), /* boss_trading_enabled */ true,
                d.max_uses_per_day(), d.restock_interval_days(),
                d.price_max(), d.epk_cheap(), d.epk_rare(), Map.of());
        assertTrue(NeutralizationScope.canTrade(EntityType.WITHER, c),
                "boss_trading_enabled=true 时凋灵可交易");
    }

    @Test
    void 全局交易关闭则都不可交易() {
        PalConfig d = PalConfig.defaults();
        PalConfig c = new PalConfig(
                d.hostile_whitelist(), d.kin_alert_radius(),
                d.anger_cooldown_seconds(), d.anger_cooldown_distance(),
                /* trading_enabled */ false, true,
                d.max_uses_per_day(), d.restock_interval_days(),
                d.price_max(), d.epk_cheap(), d.epk_rare(), Map.of());
        assertFalse(NeutralizationScope.canTrade(EntityType.ZOMBIE, c),
                "trading_enabled=false 时普通生物也不开交易");
    }

    @Test
    void 白名单生物不可交易() {
        // pillager 在白名单 → 未中立化 → 不可交易
        assertFalse(NeutralizationScope.canTrade(EntityType.PILLAGER, PalConfig.defaults()));
    }

    // ── isBoss / 白名单有效性 ──

    @Test
    void Boss判定() {
        assertTrue(NeutralizationScope.isBoss(EntityType.WITHER), "凋灵");
        assertTrue(NeutralizationScope.isBoss(EntityType.WARDEN), "监守者");
        assertFalse(NeutralizationScope.isBoss(EntityType.ZOMBIE), "僵尸不是 Boss");
    }

    @Test
    void 白名单有效性校验() {
        // 末影龙未适配 → 列入白名单是无效配置
        assertTrue(NeutralizationScope.isIneffectiveWhitelistEntry("minecraft:ender_dragon"));
        // 僵尸已适配 → 列入白名单是有效配置
        assertFalse(NeutralizationScope.isIneffectiveWhitelistEntry("minecraft:zombie"));
    }
}
