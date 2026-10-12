package top.windyvalley.peaceandlove.trade;

import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;

/**
 * 补货判定（T-TRADE-004）—— 语义对齐原版村民 {@code Villager#shouldRestock()} 的双时钟模型，
 * 但去掉其职业经验 / demand 涨价 / 每日次数上限。
 *
 * <p><b>两个时钟</b>（对应村民的两条腿，见 {@code Villager.shouldRestock}）：
 * <ul>
 *   <li><b>滚动间隔</b>用单调的 {@code level.getGameTime()}（世界总 tick，每 tick +1，
 *       命令/睡觉都改不了）：距上次实际补货达到 {@code restock_interval_days} 即允许补。</li>
 *   <li><b>跨自然日</b>用 {@code level.getDayTime()}（一天 24000，会被玩家睡觉快进、
 *       也会被 {@code /time} 改）：{@code dayTime/24000} 的天数比上次补货时变大即允许补。
 *       <b>睡觉让怪物提前补货就是走这条腿</b>——与村民同源（睡觉经 level.setDayTime 推进）。</li>
 * </ul>
 *
 * <p>两条腿 OR，且都还要过 {@code hasStockedOut}（对应村民 {@code needsToRestock}）：
 * 没有任何报价被买光就什么都不做、<b>锚点也不推进</b>，避免「上次补货时刻」因空转与真实购买脱节。
 *
 * <p><b>离线补算</b>：区块卸载期间实体不 tick，重挂后首 tick 一次性比较两个时钟，
 * 跨过多少间隔/天都只补一次（与村民 flag OR 一致），锚点随后定到当前。
 *
 * <p>纯算术、不依赖 Minecraft 运行时（不碰 Item/Level），可无 bootstrap 单测。
 * 唯一触碰原版 API 的动作是 {@link #resetUses}（绝不是 {@code Villager.restock()}——
 * 它先 {@code updateDemand()} 做 catchUpDemand 涨价）。
 */
public final class RestockManager {

    /** 一个游戏日的 tick 数。 */
    public static final long DAY_TICKS = 24_000L;

    private RestockManager() {
    }

    /** 补货周期（游戏日，支持小数）→ tick 数，至少 1 tick。 */
    public static long intervalTicks(double intervalDays) {
        long t = Math.round(intervalDays * DAY_TICKS);
        return Math.max(1L, t);
    }

    /** 是否至少有一条报价已售罄（对应村民 needsToRestock）。 */
    public static boolean anyOutOfStock(MerchantOffers offers) {
        for (MerchantOffer offer : offers) {
            if (offer.isOutOfStock()) {
                return true;
            }
        }
        return false;
    }

    /**
     * 补货判定结果。
     *
     * @param restocked   本 tick 是否应清零 uses
     * @param newLastGame 判定后应持久化的「上次补货 gameTime」
     * @param newLastDay  判定后应持久化的「上次补货所在自然日」（dayTime/24000）
     */
    public record RestockResult(boolean restocked, long newLastGame, long newLastDay) {
    }

    /**
     * 双时钟补货判定（纯算术，可单测）。
     *
     * @param gameTime      当前 {@code level.getGameTime()}（单调）
     * @param dayTime       当前 {@code level.getDayTime()}（睡觉/时间命令可快进）
     * @param lastGame      上次补货的 gameTime；{@code <0}=首次（仅锚定，不补）
     * @param lastDay       上次补货所在自然日（dayTime/24000）；首次值忽略
     * @param intervalDays  滚动补货周期（游戏日，支持小数）
     * @param hasStockedOut 是否存在已售罄报价（needsToRestock）；false 则即使到点也不补、锚点不动
     */
    public static RestockResult evaluate(long gameTime, long dayTime,
                                         long lastGame, long lastDay,
                                         double intervalDays, boolean hasStockedOut) {
        long today = dayTime / DAY_TICKS;
        // 首次：锚定两个时钟，不补货（报价刚组装，uses 本就是 0）。
        if (lastGame < 0L) {
            return new RestockResult(false, gameTime, today);
        }
        // 没有买光的报价：不补，且锚点保持（与村民 needsToRestock 一致）。
        if (!hasStockedOut) {
            return new RestockResult(false, lastGame, lastDay);
        }
        boolean byInterval = gameTime - lastGame >= intervalTicks(intervalDays);
        boolean byDayChange = today > lastDay;   // 睡过一夜（或 /time 跨天）
        if (byInterval || byDayChange) {
            return new RestockResult(true, gameTime, today);
        }
        return new RestockResult(false, lastGame, lastDay);
    }

    /**
     * 把整份报价单的购买次数清零（唯一触碰原版 API 的动作，非 Villager.restock）。
     */
    public static void resetUses(MerchantOffers offers) {
        for (MerchantOffer offer : offers) {
            offer.resetUses();
        }
    }
}
