package top.windyvalley.peaceandlove.scope;

import net.minecraft.world.entity.EntityType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import top.windyvalley.peaceandlove.config.PalConfig;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 门控真值表补齐（T-TEST-002.2）：4 种基础组合参数化 + 未适配生物直接断言 +
 * 第三方/未知 id 一律 false + 白名单动态变更同一入口立即改变。
 *
 * <p>与 {@link NeutralizationScopeTest} 互补：后者已覆盖各场景的手写用例与 Boss，
 * 这里把「isAdapted × inWhitelist」四组合收敛成一张参数化真值表，并补上对
 * 末影龙（未适配）与未知 id 的直接断言。
 */
class NeutralizationScopeTruthTableTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    private static PalConfig cfg(List<String> whitelist) {
        PalConfig d = PalConfig.defaults();
        return new PalConfig(
                whitelist,
                d.kin_alert_radius(), d.anger_cooldown_seconds(), d.anger_cooldown_distance(),
                d.trading_enabled(), d.boss_trading_enabled(),
                d.max_uses_per_day(), d.restock_interval_days(),
                d.price_max(), d.epk_cheap(), d.epk_rare(), d.price_overrides());
    }

    /** 4 种基础组合：已适配 zombie / 未适配 cow × 在/不在白名单。 */
    @ParameterizedTest(name = "[{index}] {0} whitelist={1} -> neutralized={2}")
    @CsvSource({
            "zombie, ,      true",   // 已适配且不在白名单 → 中立化
            "zombie, zombie, false",  // 已适配但在白名单 → 保持原版
            "cow,    ,      false",  // 未适配且不在白名单 → 保持原版
            "cow,    cow,    false",  // 未适配但在白名单 → 配置无效，仍原版
    })
    void 真值表_四种基础组合(String entity, String whitelist, boolean expected) {
        EntityType<?> type = entityType(entity);
        PalConfig c = cfg(whitelist == null || whitelist.isBlank()
                ? List.of() : List.of("minecraft:" + whitelist));
        org.junit.jupiter.api.Assertions.assertEquals(expected,
                NeutralizationScope.isNeutralized(type, c),
                entity + " whitelist=" + whitelist);
        // canTrade 恒满足：能交易必先中立化；未中立化的组合一律不能交易
        org.junit.jupiter.api.Assertions.assertEquals(expected,
                NeutralizationScope.canTrade(type, c));
    }

    @Test
    void 末影龙未适配_无论是否在白名单_都不中立化() {
        assertFalse(AdaptedMobs.isAdapted(EntityType.ENDER_DRAGON),
                "前置：末影龙不在 v1.0 适配列表");
        assertFalse(NeutralizationScope.isNeutralized(
                EntityType.ENDER_DRAGON, PalConfig.defaults()));
        assertFalse(NeutralizationScope.isNeutralized(
                EntityType.ENDER_DRAGON, cfg(List.of("minecraft:ender_dragon"))),
                "末影龙即使列入白名单（无效配置）也不中立化");
        assertFalse(NeutralizationScope.canTrade(
                EntityType.ENDER_DRAGON, PalConfig.defaults()));
    }

    @ParameterizedTest(name = "[{index}] 未知 id {0} 一律视为无效/不生效")
    @CsvSource({
            "minecraft:does_not_exist",
            "somemod:custom_hostile",   // 第三方 Mod 生物，未注册到适配列表
            "minecraft:",
    })
    void 第三方或未知id_一律不生效(String unknownId) {
        assertTrue(NeutralizationScope.isIneffectiveWhitelistEntry(unknownId),
                "未知/第三方 id 列入白名单是无效配置：" + unknownId);
        // 未知 id 进白名单必须是惰性的：不影响任何已适配/未适配生物的判定
        PalConfig c = cfg(List.of(unknownId));
        assertTrue(NeutralizationScope.isNeutralized(EntityType.ZOMBIE, c),
                "含未知 id 的白名单不应改变僵尸的中立化：" + unknownId);
        assertTrue(NeutralizationScope.canTrade(EntityType.ZOMBIE, c));
        assertFalse(NeutralizationScope.isNeutralized(EntityType.COW, c),
                "未适配牛在任何白名单下都保持原版：" + unknownId);
        // 结构免疫：任何未注册/未适配的 EntityType 都不可能命中适配常量集合
        assertFalse(AdaptedMobs.isAdapted(EntityType.COW));
        assertFalse(AdaptedMobs.isAdapted(EntityType.ENDER_DRAGON));
    }

    @Test
    void 白名单动态变更_同一判定入口立即改变_不缓存() {
        EntityType<?> zombie = EntityType.ZOMBIE;
        // 同一逻辑实体，白名单从空 → 含 zombie，判定必须立即翻转
        assertTrue(NeutralizationScope.isNeutralized(zombie, cfg(List.of())));
        assertFalse(NeutralizationScope.isNeutralized(
                zombie, cfg(List.of("minecraft:zombie"))));
        // 再移出白名单 → 重新中立化
        assertTrue(NeutralizationScope.isNeutralized(zombie, cfg(List.of())));
    }

    private static EntityType<?> entityType(String shortId) {
        EntityType<?> t = net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE
                .get(net.minecraft.resources.ResourceLocation.parse("minecraft:" + shortId));
        if (t == null) {
            throw new AssertionError("测试引导失败：注册表无 minecraft:" + shortId);
        }
        return t;
    }
}
