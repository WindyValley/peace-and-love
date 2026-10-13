package top.windyvalley.peaceandlove.trade;

import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link TradeSpec} 单测。
 *
 * <p>{@code toOffer()} 引用 {@link Items}（注册表常量），需先 bootstrap。
 */
class TradeSpecTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    @Test
    void 普通价格_单输入槽_数量与产物正确() {
        TradeSpec spec = new TradeSpec(Items.ROTTEN_FLESH, 2, 16, 1.0);
        MerchantOffer o = spec.toOffer();

        // getCostA() 返回 ItemStack（ItemCost 仅用于构造），用 ItemStack 访问器
        assertEquals(16, o.getCostA().getCount());
        assertEquals(Items.EMERALD, o.getCostA().getItem());
        assertTrue(o.getCostB().isEmpty(), "价格 <= 64 不应有第二槽");
        ItemStack result = o.getResult();
        assertEquals(Items.ROTTEN_FLESH, result.getItem());
        assertEquals(2, result.getCount());
    }

    @Test
    void 高价_拆成双输入槽_合计等于价格() {
        TradeSpec spec = new TradeSpec(Items.IRON_INGOT, 1, 117, 1.0 / 120);
        MerchantOffer o = spec.toOffer();

        assertEquals(64, o.getCostA().getCount(), "第一槽封顶 64");
        ItemStack b = o.getCostB();
        assertFalse(b.isEmpty(), "价格 117 应有第二槽");
        assertEquals(53, b.getCount(), "第二槽 = 117-64");
        assertEquals(Items.EMERALD, b.getItem());
    }

    @Test
    void 报价语义_每日一次_零经验_零价格乘数() {
        MerchantOffer o = new TradeSpec(Items.BONE, 2, 8, 1.0).toOffer();
        assertEquals(1, o.getMaxUses(), "每补货周期限购 1 次");
        assertEquals(0, o.getXp(), "怪物交易不给村民经验");
        assertEquals(0.0F, o.getPriceMultiplier(), 0.0001F, "禁用需求量价格漂移");
    }

    @Test
    void 限购次数可配_透传到maxUses() {
        MerchantOffer o = new TradeSpec(Items.BONE, 1, 8, 1.0).toOffer(4);
        assertEquals(4, o.getMaxUses(), "max_uses_per_day 应透传");
    }

    @Test
    void 限购次数非法_抛异常() {
        assertThrows(IllegalArgumentException.class,
                () -> new TradeSpec(Items.BONE, 1, 8, 1.0).toOffer(0));
    }

    @Test
    void 非法入参_抛异常() {
        assertThrows(IllegalArgumentException.class,
                () -> new TradeSpec(null, 1, 1, 1.0));
        assertThrows(IllegalArgumentException.class,
                () -> new TradeSpec(Items.BONE, 0, 1, 1.0));
        assertThrows(IllegalArgumentException.class,
                () -> new TradeSpec(Items.BONE, 1, 0, 1.0));
        assertThrows(IllegalArgumentException.class,
                () -> new TradeSpec(Items.BONE, 1, 129, 1.0), "超过双槽 128");
    }
}
