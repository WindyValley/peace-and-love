package top.windyvalley.peaceandlove.trade;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;

import java.util.Optional;

/**
 * 一条怪物掉落物的交易规格 —— design §3.4。
 *
 * <p>把定价结果（绿宝石价格）与掉落物产出绑定，并能生成原版
 * {@link MerchantOffer}，直接喂给原版交易 GUI。
 *
 * @param item  出售给玩家的掉落物
 * @param count 单次产出数量 = 原版一次击杀该物品的最大掉落量（looting 0 上界）
 * @param price 绿宝石价格，[1, {@code priceMax}]（默认上限 128）
 * @param epk   期望每次击杀产出量，供 /pal debug 与诊断展示
 */
public record TradeSpec(Item item, int count, int price, double epk) {

    /** 双输入槽各自的堆叠上限：单价超过 64 时拆成两份绿宝石。 */
    private static final int PER_SLOT = 64;

    public TradeSpec {
        if (item == null) {
            throw new IllegalArgumentException("交易物品不能为 null");
        }
        if (count < 1) {
            throw new IllegalArgumentException("单次产出必须 >= 1，实际: " + count);
        }
        if (price < 1) {
            throw new IllegalArgumentException("价格必须 >= 1，实际: " + price);
        }
        if (price > 128) {
            // MerchantOffer 双输入槽 64+64 的硬上限（ADR-003）
            throw new IllegalArgumentException("价格超过双槽上限 128: " + price);
        }
    }

    /**
     * 转为原版交易报价。
     *
     * <p>固定语义（ADR-003）：
     * <ul>
     *   <li>{@code maxUses}：每个补货周期内该报价可购买次数（config
     *       {@code max_uses_per_day}，默认 1）；</li>
     *   <li>经验 {@code xp=0}：怪物交易不给村民经验、不显示等级条；</li>
     *   <li>{@code priceMultiplier=0}：禁用原版需求量导致的价格漂移，保证定价确定；</li>
     *   <li>价格 &gt; 64 拆成两个绿宝石输入槽。</li>
     * </ul>
     *
     * @param maxUses 每补货周期限购次数，调用方来自 config，至少 1
     */
    public MerchantOffer toOffer(int maxUses) {
        if (maxUses < 1) {
            throw new IllegalArgumentException("maxUses 必须 >= 1，实际: " + maxUses);
        }
        ItemCost costA = new ItemCost(Items.EMERALD, Math.min(price, PER_SLOT));
        Optional<ItemCost> costB = price > PER_SLOT
                ? Optional.of(new ItemCost(Items.EMERALD, price - PER_SLOT))
                : Optional.empty();
        return new MerchantOffer(
                costA,
                costB,
                new ItemStack(item, count),
                /* maxUses         */ maxUses,
                /* xp              */ 0,
                /* priceMultiplier */ 0.0F
        );
    }

    /** 默认限购 1 次的便捷重载（与 config 默认值一致）。 */
    public MerchantOffer toOffer() {
        return toOffer(1);
    }
}
