package top.windyvalley.peaceandlove.trade;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import top.windyvalley.peaceandlove.config.PalConfig;
import top.windyvalley.peaceandlove.pricing.PriceTable;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

import java.util.List;

/**
 * 运行时报价单组装器（T-TRADE-002.2）—— 为一只生物把定价表组装成原版
 * {@link MerchantOffers}，供 {@code MobMerchantMixin.getOffers()} 接入。
 *
 * <p>它是<b>定价域与交易域之间的薄转换层</b>，本身无状态：
 * <ul>
 *   <li>{@link PriceTable} 已在启动/reload 时构好并缓存了每条 {@link TradeSpec}
 *       （价格、掉落量），本类只取列表、调 {@link TradeSpec#toOffer()}，O(掉落物种类)，
 *       不重复任何定价计算；</li>
 *   <li>能否交易一律以 {@link NeutralizationScope#canTrade} 为唯一权威 —— 未适配 /
 *       在白名单 / trading_enabled=false / Boss 未开 boss_trading_enabled，全部返回空单。</li>
 * </ul>
 *
 * <p><b>缓存边界</b>：本方法每次返回<b>新的</b> {@link MerchantOffers}（报价对象的使用次数
 * maxUses/uses 是每只怪物各自的交易状态，不能在多只同种怪物间共享同一个 MerchantOffer 实例，
 * 否则一只买光会连累所有同类）。「组装一次、缓存复用」的职责在 {@code MobMerchantMixin}
 * 的 {@code pal$offers} 字段（每只生物懒加载一份），不在本组装器。
 *
 * <p>右键打开交易界面、mixin 实际调用与 reload 后旧生物报价刷新，在 T-TRADE-003 接线联调。
 */
public final class TradeOfferBuilder {

    private TradeOfferBuilder() {
    }

    /**
     * 组装一只生物当前配置下的整份报价单。
     *
     * @param type   生物类型
     * @param config 当前生效配置（门控读它，不缓存）
     * @param table  已构建的不可变定价表
     * @return 门控不通过或该生物无可售掉落时返回空 {@link MerchantOffers}（非 null）
     */
    public static MerchantOffers assemble(EntityType<?> type, PalConfig config, PriceTable table) {
        MerchantOffers offers = new MerchantOffers();
        if (!NeutralizationScope.canTrade(type, config)) {
            return offers;
        }
        List<TradeSpec> specs = table.offersFor(type);
        for (TradeSpec spec : specs) {
            offers.add(spec.toOffer());
        }
        return offers;
    }
}
