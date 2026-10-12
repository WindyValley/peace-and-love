package top.windyvalley.peaceandlove.pricing;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import top.windyvalley.peaceandlove.config.PalConfig;
import top.windyvalley.peaceandlove.pricing.LootTableScanner.DropEntry;
import top.windyvalley.peaceandlove.trade.TradeSpec;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link PriceTable} 纯构建逻辑单测（T-PRICE-003）。
 *
 * <p>不碰战利品表扫描（那是 001，另有真机黄金回归），只喂 {@link DropEntry} 验证：
 * 定价/override/同物品多条保留/不可变/诊断。需注册表 bootstrap 以取得 EntityType/Item。
 */
class PriceTableTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    private static DropEntry drop(EntityType<?> type, Item item, double epk, int countMax) {
        return new DropEntry(type, BuiltInRegistries.ENTITY_TYPE.getKey(type),
                item, BuiltInRegistries.ITEM.getKey(item), epk, countMax, false);
    }

    private static PalConfig withOverrides(Map<String, Integer> overrides) {
        PalConfig d = PalConfig.defaults();
        return new PalConfig(
                d.hostile_whitelist(),
                d.kin_alert_radius(), d.anger_cooldown_seconds(), d.anger_cooldown_distance(),
                d.trading_enabled(), d.boss_trading_enabled(),
                d.max_uses_per_day(), d.restock_interval_days(),
                d.price_max(), d.epk_cheap(), d.epk_rare(), overrides);
    }

    @Test
    void 默认配置_价格来自曲线_产出取countMax() {
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        PriceTable t = PriceTable.build(List.of(flesh), PalConfig.defaults()).table();

        List<TradeSpec> offers = t.offersFor(EntityType.ZOMBIE, Items.ROTTEN_FLESH);
        assertEquals(1, offers.size());
        TradeSpec s = offers.get(0);
        assertEquals(2, s.count(), "产出量 = looting0 上界 countMax");
        assertEquals(ConfigurablePriceCurve.price(0.5, PalConfig.defaults()), s.price());
        assertEquals(0.5, s.epk(), 1e-9);
        assertEquals(1, t.size());
        assertTrue(t.entities().contains(EntityType.ZOMBIE));
    }

    @Test
    void 同一物品多条掉落_保留为多条报价() {
        // 史莱姆黏液球：互斥分支，2 个/较高 epk 与 1 个/较低 epk
        DropEntry a = drop(EntityType.SLIME, Items.SLIME_BALL, 0.105, 2);
        DropEntry b = drop(EntityType.SLIME, Items.SLIME_BALL, 0.045, 1);
        PriceTable t = PriceTable.build(List.of(a, b), PalConfig.defaults()).table();

        List<TradeSpec> offers = t.offersFor(EntityType.SLIME, Items.SLIME_BALL);
        assertEquals(2, offers.size(), "同物品不同掉落量必须保留两条，不得压成单值");
        assertEquals(2, offers.get(0).count());
        assertEquals(1, offers.get(1).count());
        // epk 越低越贵
        assertTrue(offers.get(1).price() > offers.get(0).price(),
                "低 epk 分支应更贵：" + offers.get(0).price() + " vs " + offers.get(1).price());
        assertEquals(2, t.offersFor(EntityType.SLIME).size());
    }

    @Test
    void 未适配或无掉落_查询返回空列表而非null() {
        PriceTable t = PriceTable.build(List.of(), PalConfig.defaults()).table();
        assertEquals(0, t.offersFor(EntityType.ZOMBIE).size());
        assertEquals(0, PriceTable.EMPTY.offersFor(EntityType.ZOMBIE, Items.ROTTEN_FLESH).size());
        assertEquals(0, PriceTable.EMPTY.size());
    }

    @Test
    void price_override命中_覆盖曲线价() {
        String key = "minecraft:zombie/minecraft:rotten_flesh";
        PalConfig cfg = withOverrides(Map.of(key, 100));
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        PriceTable.BuildResult r = PriceTable.build(List.of(flesh), cfg);

        assertEquals(100, r.table().offersFor(EntityType.ZOMBIE, Items.ROTTEN_FLESH).get(0).price());
        assertTrue(r.warnings().stream().noneMatch(w -> w.contains("未匹配")),
            "命中的 override 不应报未匹配：" + r.warnings());
    }

    @Test
    void price_override越界_clamp并告警() {
        String key = "minecraft:zombie/minecraft:rotten_flesh";
        PalConfig cfg = withOverrides(Map.of(key, 999)); // 超过 128 硬上限
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        PriceTable.BuildResult r = PriceTable.build(List.of(flesh), cfg);

        assertEquals(128, r.table().offersFor(EntityType.ZOMBIE, Items.ROTTEN_FLESH).get(0).price());
        assertTrue(r.warnings().stream().anyMatch(w -> w.contains("越界")), r.warnings().toString());
    }

    @Test
    void price_override无对应掉落_告警但不崩() {
        PalConfig cfg = withOverrides(Map.of("minecraft:zombie/minecraft:diamond", 10));
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        PriceTable.BuildResult r = PriceTable.build(List.of(flesh), cfg);

        assertTrue(r.warnings().stream().anyMatch(w -> w.contains("未匹配")), r.warnings().toString());
        assertEquals(1, r.table().size());
    }

    @Test
    void 构建结果不可变_返回列表不可修改() {
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        PriceTable t = PriceTable.build(List.of(flesh), PalConfig.defaults()).table();

        assertThrows(UnsupportedOperationException.class,
                () -> t.offersFor(EntityType.ZOMBIE).add(null));
        assertThrows(UnsupportedOperationException.class,
                () -> t.offersFor(EntityType.ZOMBIE, Items.ROTTEN_FLESH).clear());
        assertThrows(UnsupportedOperationException.class,
                () -> t.entities().clear());
    }

    @Test
    void 改输入drops不影响已构建的表() {
        List<DropEntry> mutable = new ArrayList<>(
                List.of(drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2)));
        PriceTable t = PriceTable.build(mutable, PalConfig.defaults()).table();
        mutable.add(drop(EntityType.ZOMBIE, Items.IRON_INGOT, 0.0083, 1));
        assertEquals(1, t.size(), "发布后外部改动源列表不得影响不可变表");
    }

    @Test
    void 构建结果带报价数与耗时() {
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        DropEntry bone = drop(EntityType.SKELETON, Items.BONE, 0.6, 2);
        PriceTable.BuildResult r = PriceTable.build(List.of(flesh, bone), PalConfig.defaults());
        assertEquals(2, r.offerCount());
        assertTrue(r.elapsedMillis() >= 0);
    }

    // ── T-PRICE-004 单调性自检 ──

    private static final String K_FLESH = "minecraft:zombie/minecraft:rotten_flesh";
    private static final String K_IRON = "minecraft:zombie/minecraft:iron_ingot";

    @Test
    void 自检_默认曲线表健康无逆序() {
        // 同生物两条：flesh 高产(epk 0.5)、iron 稀有(epk 0.0083)，曲线天然单调
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        DropEntry iron = drop(EntityType.ZOMBIE, Items.IRON_INGOT, 0.0083, 1);
        PriceTable t = PriceTable.build(List.of(flesh, iron), PalConfig.defaults()).table();

        PriceTable.SelfCheck chk = PriceTable.selfCheck(t, PalConfig.defaults());
        assertEquals(2, chk.totalOffers());
        assertTrue(chk.healthy(), "默认参数不应有逆序：" + chk.inversions());
        // 方向正确：稀有铁锭价比高产腐肉高（撞限计数另有专门用例）
        List<TradeSpec> z = t.offersFor(EntityType.ZOMBIE);
        int fleshPrice = z.stream().filter(s -> s.item() == Items.ROTTEN_FLESH).findFirst().orElseThrow().price();
        int ironPrice = z.stream().filter(s -> s.item() == Items.IRON_INGOT).findFirst().orElseThrow().price();
        assertTrue(ironPrice > fleshPrice, "稀有铁锭应更贵：" + ironPrice + ">" + fleshPrice);
    }

    @Test
    void 自检_override填反_检出逆序对() {
        // flesh epk 大(0.5) 却 override 成 100；iron epk 小(0.01) 却 override 成 10
        // → 更稀有的反而更便宜 = 逆序
        PalConfig cfg = withOverrides(Map.of(K_FLESH, 100, K_IRON, 10));
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        DropEntry iron = drop(EntityType.ZOMBIE, Items.IRON_INGOT, 0.01, 1);
        PriceTable t = PriceTable.build(List.of(flesh, iron), cfg).table();

        PriceTable.SelfCheck chk = PriceTable.selfCheck(t, cfg);
        assertEquals(1, chk.inversions().size(), "应检出恰好一对逆序：" + chk.inversions());
        assertFalse(chk.healthy());
        String desc = chk.inversions().get(0);
        assertTrue(desc.contains("rotten_flesh") && desc.contains("iron_ingot"), desc);
    }

    @Test
    void 自检_同价不同epk的平台期_不算逆序() {
        // 两个 epk 不同但都被 override 成同一价（撞顶平台期），不构成逆序
        PalConfig cfg = withOverrides(Map.of(K_FLESH, 64, K_IRON, 64));
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        DropEntry iron = drop(EntityType.ZOMBIE, Items.IRON_INGOT, 0.01, 1);
        PriceTable t = PriceTable.build(List.of(flesh, iron), cfg).table();

        PriceTable.SelfCheck chk = PriceTable.selfCheck(t, cfg);
        assertTrue(chk.healthy(), "同价平台期不应判逆序：" + chk.inversions());
    }

    @Test
    void 自检_撞上下限计数正确() {
        PalConfig cfg = withOverrides(Map.of(K_FLESH, 1, K_IRON, 128));
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        DropEntry iron = drop(EntityType.ZOMBIE, Items.IRON_INGOT, 0.01, 1);
        PriceTable t = PriceTable.build(List.of(flesh, iron), cfg).table();

        PriceTable.SelfCheck chk = PriceTable.selfCheck(t, cfg);
        assertEquals(1, chk.lowerClamped(), "flesh=1 撞下限");
        assertEquals(1, chk.upperClamped(), "iron=128 撞上限");
        // flesh epk 大价1、iron epk 小价128：方向正确（稀有更贵），无逆序
        assertTrue(chk.healthy());
    }

    @Test
    void 自检_空表不抛异常() {
        PriceTable.SelfCheck chk = PriceTable.selfCheck(PriceTable.EMPTY, PalConfig.defaults());
        assertEquals(0, chk.totalOffers());
        assertTrue(chk.healthy());
    }
}
