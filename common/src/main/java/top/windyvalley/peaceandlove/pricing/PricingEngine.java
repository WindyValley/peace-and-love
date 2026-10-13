package top.windyvalley.peaceandlove.pricing;

/**
 * 对数曲线定价引擎 —— ADR-003 的纯数学核心。
 *
 * <p>把掉落物的「每击杀期望产出」(epk) 映射为 [1, max] 的整数绿宝石价：
 * <pre>
 * pos   = log(cheap / epk) / log(cheap / rare)     // 归一化到 [0,1]
 * price = clamp(roundHalfEven(1 + (max-1) × pos), 1, max)
 * </pre>
 *
 * <p>取整用<b>半数取偶（banker's rounding，{@link Math#rint}）</b>而非
 * {@code Math.round} 的半数进位：定价黄金基准（spike 产出的
 * {@code final_pricing_128.json}，T-TEST-001 以零误差钉死）由 Python
 * {@code round()} 生成，Python 采用 HALF_EVEN。全 110 条基线路径中唯一落在
 * x.5 的是 rabbit/rabbit_foot（epk=0.1 恰使 pos=0.5：cheap/epk=20、
 * cheap/rare=400=20²）。Java 必须复现同一舍入，否则该条差 1。兔子不是 v1.0
 * 适配生物、不进实际报价表，故对 70 条在售价格零影响（真机等值已证）。
 *
 * <p>性质：产出每减半，价格等量上升（等比稀有度 → 等差价格）；
 * epk 越小（越稀有）价格越高，全局单调不增（相对 epk 单调不增）。
 *
 * <p>本类<b>不依赖任何 Minecraft 类</b>（钳制用 JDK 21 的 {@link Math#clamp}，
 * 语义与 {@code Mth.clamp} 一致），因此是 L1 基础设施，可纯 JUnit 覆盖，
 * 也便于为后续 MC 版本隔离差异。
 */
public final class PricingEngine {

    private PricingEngine() {
    }

    /**
     * 按对数曲线计算单价。
     *
     * @param epk   期望每次击杀产出量（looting 0 基准）；&le;0 视为「理论不掉落」，给最高价
     * @param cheap 廉价锚点：epk &ge; 此值时价格为 1（必须 &gt; rare 且 &gt; 0）
     * @param rare  稀有锚点：epk &le; 此值时价格为 max（必须 &gt; 0）
     * @param max   价格上限（{@code MerchantOffer} 双槽限制下为 128，必须 &ge; 1）
     * @return 钳制在 [1, max] 的整数价格
     * @throws IllegalArgumentException 锚点参数非法（max&lt;1、锚点非正、cheap&le;rare）
     */
    public static int price(double epk, double cheap, double rare, int max) {
        if (max < 1) {
            throw new IllegalArgumentException("价格上限必须 >= 1，实际: " + max);
        }
        if (cheap <= 0 || rare <= 0) {
            throw new IllegalArgumentException(
                    "定价锚点必须为正: cheap=" + cheap + " rare=" + rare);
        }
        if (cheap <= rare) {
            throw new IllegalArgumentException(
                    "廉价锚点必须大于稀有锚点: cheap=" + cheap + " rare=" + rare);
        }

        // 边界：理论不掉落给最高价；达到/超过廉价锚点给最低价。
        if (epk <= 0) {
            return max;
        }
        if (epk >= cheap) {
            return 1;
        }
        if (epk <= rare) {
            return max;
        }

        double pos = Math.log(cheap / epk) / Math.log(cheap / rare);
        // HALF_EVEN（Math.rint）对齐 Python spike/黄金基准的 round，见类注释。
        long rounded = (long) Math.rint(1 + (max - 1) * pos);
        return Math.clamp(rounded, 1, max);
    }
}
