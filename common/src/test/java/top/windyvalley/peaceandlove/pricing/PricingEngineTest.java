package top.windyvalley.peaceandlove.pricing;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link PricingEngine} 对数曲线单测 —— 纯数学，无 MC 依赖。
 *
 * <p>默认锚点取自配置：cheap=2.0、rare=0.005、max=128（ADR-003）。
 * 对 spike 全量 110 条数据的回归校验另由独立校验脚本完成，不耦合进测试套件。
 */
class PricingEngineTest {

    private static final double CHEAP = 2.0;
    private static final double RARE = 0.005;
    private static final int MAX = 128;

    private static int price(double epk) {
        return PricingEngine.price(epk, CHEAP, RARE, MAX);
    }

    @Test
    void 廉价锚点及以上_价格为1() {
        assertEquals(1, price(2.0));
        assertEquals(1, price(6.0));   // 高于廉价锚点仍钳到 1
    }

    @Test
    void 稀有锚点及以下_价格为上限() {
        assertEquals(MAX, price(0.005));
        assertEquals(MAX, price(0.001));
    }

    @Test
    void 零或负epk_视为不掉落_给最高价() {
        assertEquals(MAX, price(0));
        assertEquals(MAX, price(-1));
    }

    @Test
    void 价格始终在合法区间() {
        for (double epk = 0.0001; epk <= 10.0; epk *= 1.05) {
            int p = price(epk);
            assertTrue(p >= 1 && p <= MAX, "epk=" + epk + " 价格越界: " + p);
        }
    }

    @Test
    void epk越小价格越高_全局单调() {
        int prev = price(10.0);
        for (double epk = 9.0; epk >= 0.0001; epk /= 1.1) {
            int cur = price(epk);
            assertTrue(cur >= prev, "epk 减小价格不应下降: " + epk);
            prev = cur;
        }
        assertEquals(1, price(10.0));
        assertEquals(MAX, price(0.0001));
    }

    @Test
    void 产出减半_价格约增14点7() {
        // ADR-003：产出每减半，价格增加约 (128-1)/log2(400) ≈ 14.7
        int p1 = price(1.0);
        int p2 = price(0.5);
        assertEquals(15, p2 - p1, 2);
    }

    @Test
    void 已知锚点值对齐spike() {
        // 取自 final_pricing_128.json 的代表条目
        assertEquals(16, price(1.0));    // 腐肉/骨头/火药
        assertEquals(30, price(0.5));    // 末影珍珠/烈焰棒
        assertEquals(94, price(0.025));  // 凋灵骷髅头颅
        assertEquals(117, price(1.0 / 120)); // 僵尸铁锭/胡萝卜/马铃薯（epk=1/120）
    }

    @Test
    void 非法上限_抛异常() {
        assertThrows(IllegalArgumentException.class,
                () -> PricingEngine.price(1.0, CHEAP, RARE, 0));
    }

    @Test
    void 非正锚点_抛异常() {
        assertThrows(IllegalArgumentException.class,
                () -> PricingEngine.price(1.0, 0, RARE, MAX));
        assertThrows(IllegalArgumentException.class,
                () -> PricingEngine.price(1.0, CHEAP, -1, MAX));
    }

    @Test
    void 廉价锚点不大于稀有锚点_抛异常() {
        assertThrows(IllegalArgumentException.class,
                () -> PricingEngine.price(1.0, 0.005, 2.0, MAX));
        assertThrows(IllegalArgumentException.class,
                () -> PricingEngine.price(1.0, 1.0, 1.0, MAX));
    }
}
