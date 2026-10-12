package top.windyvalley.peaceandlove.trade;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link RestockManager} 双时钟补货判定单测（纯算术，不 bootstrap MC）。
 *
 * <p>对齐原版村民 {@code Villager#shouldRestock}：单调 gameTime 管滚动间隔，
 * dayTime/24000 管跨自然日（睡觉快进），OR 触发，且要求有售罄报价（needsToRestock）。
 */
class RestockManagerTest {

    private static final long T0 = 100_000L;
    private static final long DAY0 = 1_000L;          // 上次补货所在自然日序号

    @Test
    void 周期换算_支持小数() {
        assertEquals(24_000L, RestockManager.intervalTicks(1.0));
        assertEquals(12_000L, RestockManager.intervalTicks(0.5), "半天 = 12000 tick");
        assertEquals(72_000L, RestockManager.intervalTicks(3.0));
        assertEquals(2_400L, RestockManager.intervalTicks(0.1));
        assertEquals(1L, RestockManager.intervalTicks(0.0), "极小值兜底为 1 tick");
    }

    @Test
    void 首次见到_锚定双时钟_不补货() {
        RestockManager.RestockResult r =
                RestockManager.evaluate(T0, DAY0 * 24_000L, -1L, 0L, 1.0, true);
        assertFalse(r.restocked());
        assertEquals(T0, r.newLastGame());
        assertEquals(DAY0, r.newLastDay());
    }

    @Test
    void 滚动间隔未到_同一天_不补() {
        RestockManager.RestockResult r = RestockManager.evaluate(
                T0 + 23_999L, DAY0 * 24_000L + 1000L, T0, DAY0, 1.0, true);
        assertFalse(r.restocked());
        assertEquals(T0, r.newLastGame(), "锚点不动");
        assertEquals(DAY0, r.newLastDay());
    }

    @Test
    void 滚动间隔到_有售罄_补货() {
        RestockManager.RestockResult r = RestockManager.evaluate(
                T0 + 24_000L, (DAY0 + 1) * 24_000L, T0, DAY0, 1.0, true);
        assertTrue(r.restocked());
        assertEquals(T0 + 24_000L, r.newLastGame());
        assertEquals(DAY0 + 1, r.newLastDay());
    }

    @Test
    void 滚动间隔到_但无售罄_不补且锚点不动() {
        // 对齐村民 needsToRestock：没有买光的报价，到点也不补，锚点不前移。
        RestockManager.RestockResult r = RestockManager.evaluate(
                T0 + 100_000L, (DAY0 + 4) * 24_000L, T0, DAY0, 1.0, false);
        assertFalse(r.restocked());
        assertEquals(T0, r.newLastGame(), "无售罄时空转，game 锚点不推进");
        assertEquals(DAY0, r.newLastDay(), "day 锚点也不推进");
    }

    @Test
    void 睡觉快进跨自然日_即使gameTime间隔没到_也补货() {
        // 玩家睡觉：getDayTime 被快进到下一天，但 getGameTime 只走了几百 tick。
        long gameTime = T0 + 500L;
        long dayTime = (DAY0 + 1) * 24_000L + 500L;
        RestockManager.RestockResult r =
                RestockManager.evaluate(gameTime, dayTime, T0, DAY0, 1.0, true);
        assertTrue(r.restocked(), "睡觉跨自然日应触发补货（村民同源）");
        assertEquals(gameTime, r.newLastGame());
        assertEquals(DAY0 + 1, r.newLastDay());
    }

    @Test
    void 睡觉跨天但无售罄_不补() {
        RestockManager.RestockResult r = RestockManager.evaluate(
                T0 + 500L, (DAY0 + 1) * 24_000L, T0, DAY0, 1.0, false);
        assertFalse(r.restocked());
        assertEquals(T0, r.newLastGame());
        assertEquals(DAY0, r.newLastDay());
    }

    @Test
    void 半天滚动周期_12000tick补货_无需跨天() {
        // interval=0.5：gameTime 走 12000 即补，即使还在同一自然日。
        RestockManager.RestockResult r = RestockManager.evaluate(
                T0 + 12_000L, DAY0 * 24_000L + 12_000L, T0, DAY0, 0.5, true);
        assertTrue(r.restocked());
        assertEquals(T0 + 12_000L, r.newLastGame());
        assertEquals(DAY0, r.newLastDay(), "仍在同一天，day 锚点不变");
    }

    @Test
    void 离线大跳_双时钟都跨过_只补一次_锚点定当前() {
        // 区块卸载期间世界推进很多：boolean OR 最多补一次；锚点定到当前时刻（对齐村民 OR flag，
        // 不做网格回卷——剩余零头并入下一周期，与村民"补一次后重新计时"一致）。
        long gameTime = T0 + 100_000L;
        long dayTime = (DAY0 + 4) * 24_000L;
        RestockManager.RestockResult r =
                RestockManager.evaluate(gameTime, dayTime, T0, DAY0, 1.0, true);
        assertTrue(r.restocked());
        assertEquals(gameTime, r.newLastGame());
        assertEquals(DAY0 + 4, r.newLastDay());
    }

    @Test
    void 间隔很长但同一天_滚动腿独立触发() {
        // 天数没涨，但 gameTime 已超间隔，滚动腿独立成立。
        RestockManager.RestockResult r = RestockManager.evaluate(
                T0 + 30_000L, DAY0 * 24_000L + 1_000L, T0, DAY0, 1.0, true);
        assertTrue(r.restocked());
        assertEquals(DAY0, r.newLastDay());
    }

    @Test
    void 边界_刚好间隔_滚动腿触发() {
        assertFalse(RestockManager.evaluate(
                T0 + 23_999L, DAY0 * 24_000L, T0, DAY0, 1.0, true).restocked());
        assertTrue(RestockManager.evaluate(
                T0 + 24_000L, DAY0 * 24_000L, T0, DAY0, 1.0, true).restocked());
    }
}
