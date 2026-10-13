package top.windyvalley.peaceandlove.trade;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import top.windyvalley.peaceandlove.config.PalConfig;
import top.windyvalley.peaceandlove.pricing.LootTableScanner.DropEntry;
import top.windyvalley.peaceandlove.pricing.PriceTable;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link TradeOfferBuilder} 运行时组装单测（T-TRADE-002.2）。
 *
 * <p>自己用 {@link DropEntry} 构造 PriceTable（不依赖真实战利品表），重点验：
 * 可交易生物逐条组装、门控各分支返回空单、每次返回独立实例（多只同种怪物不共享）。
 */
class TradeOfferBuilderTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    private static DropEntry drop(EntityType<?> type, net.minecraft.world.item.Item item,
                                  double epk, int countMax) {
        return new DropEntry(type, BuiltInRegistries.ENTITY_TYPE.getKey(type),
                item, BuiltInRegistries.ITEM.getKey(item), epk, countMax, false);
    }

    /** 复制默认配置，覆盖交易相关三项。 */
    private static PalConfig cfg(List<String> whitelist, boolean trading, boolean bossTrading) {
        PalConfig d = PalConfig.defaults();
        return new PalConfig(
                whitelist,
                d.kin_alert_radius(), d.anger_cooldown_seconds(), d.anger_cooldown_distance(),
                trading, bossTrading, d.max_uses_per_day(), d.restock_interval_days(),
                d.price_max(), d.epk_cheap(), d.epk_rare(), d.price_overrides());
    }

    private PriceTable tableOf(DropEntry... drops) {
        return PriceTable.build(List.of(drops), PalConfig.defaults()).table();
    }

    @Test
    void 可交易生物_逐条组装成MerchantOffers() {
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        DropEntry iron = drop(EntityType.ZOMBIE, Items.IRON_INGOT, 0.0083, 1);
        PriceTable table = tableOf(flesh, iron);

        MerchantOffers offers =
                TradeOfferBuilder.assemble(EntityType.ZOMBIE, PalConfig.defaults(), table);

        assertNotNull(offers);
        assertEquals(2, offers.size());
        // 产物/限购语义来自 TradeSpec.toOffer
        MerchantOffer first = offers.get(0);
        assertEquals(Items.ROTTEN_FLESH, first.getResult().getItem());
        assertEquals(2, first.getResult().getCount());
        assertEquals(1, first.getMaxUses());
        // 价格与定价表一致
        int expected = table.offersFor(EntityType.ZOMBIE, Items.ROTTEN_FLESH).get(0).price();
        assertEquals(expected, first.getCostA().getCount() + first.getCostB().getCount());
    }

    @Test
    void 默认白名单内生物_返回空单() {
        // pillager 在默认 hostile_whitelist 中 → 保持原版敌对，不交易
        DropEntry arrow = drop(EntityType.PILLAGER, Items.ARROW, 0.5, 1);
        PriceTable table = tableOf(arrow);

        MerchantOffers offers =
                TradeOfferBuilder.assemble(EntityType.PILLAGER, PalConfig.defaults(), table);
        assertTrue(offers.isEmpty());
    }

    @Test
    void 未适配生物_返回空单() {
        DropEntry beef = drop(EntityType.COW, Items.BEEF, 1.0, 2);
        PriceTable table = tableOf(beef);

        MerchantOffers offers =
                TradeOfferBuilder.assemble(EntityType.COW, PalConfig.defaults(), table);
        assertTrue(offers.isEmpty(), "牛未适配，即使表里有条目也不交易");
    }

    @Test
    void 全局交易开关关_返回空单() {
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        PriceTable table = tableOf(flesh);
        PalConfig c = cfg(PalConfig.defaults().hostile_whitelist(), false, false);

        assertTrue(TradeOfferBuilder.assemble(EntityType.ZOMBIE, c, table).isEmpty());
    }

    @Test
    void boss默认不开交易_开关打开后可交易() {
        // 凋灵适配但属 Boss；构造表里放一条下界之星（真实走代码掉落，这里只测组装）
        DropEntry star = drop(EntityType.WITHER, Items.NETHER_STAR, 0.001, 1);
        PriceTable table = tableOf(star);
        PalConfig off = cfg(PalConfig.defaults().hostile_whitelist(), true, false);
        PalConfig on = cfg(PalConfig.defaults().hostile_whitelist(), true, true);

        assertTrue(TradeOfferBuilder.assemble(EntityType.WITHER, off, table).isEmpty(),
                "boss_trading_enabled=false 时空单");
        MerchantOffers offers = TradeOfferBuilder.assemble(EntityType.WITHER, on, table);
        assertEquals(1, offers.size());
        assertEquals(Items.NETHER_STAR, offers.get(0).getResult().getItem());
    }

    @Test
    void 表里没有该生物_返回空单不抛异常() {
        PriceTable table = tableOf(drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2));
        MerchantOffers offers =
                TradeOfferBuilder.assemble(EntityType.SKELETON, PalConfig.defaults(), table);
        assertNotNull(offers);
        assertTrue(offers.isEmpty());
    }

    @Test
    void 每次组装返回独立实例_多只同种怪物不共享报价状态() {
        DropEntry flesh = drop(EntityType.ZOMBIE, Items.ROTTEN_FLESH, 0.5, 2);
        PriceTable table = tableOf(flesh);

        MerchantOffers a = TradeOfferBuilder.assemble(EntityType.ZOMBIE, PalConfig.defaults(), table);
        MerchantOffers b = TradeOfferBuilder.assemble(EntityType.ZOMBIE, PalConfig.defaults(), table);
        assertNotSame(a, b, "两次调用应得到不同 MerchantOffers 容器");
        assertNotSame(a.get(0), b.get(0), "MerchantOffer 也不得共享（uses 是每只各自的状态）");
        // 买光 a 不影响 b
        a.get(0).increaseUses();
        assertEquals(1, a.get(0).getUses());
        assertEquals(0, b.get(0).getUses());
        assertFalse(b.get(0).isOutOfStock());
    }
}
