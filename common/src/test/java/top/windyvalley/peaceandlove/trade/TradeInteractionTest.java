package top.windyvalley.peaceandlove.trade;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * T-TRADE-003 右键交易门控真值表 —— 纯逻辑，不需要 Mob 实例。
 *
 * <p>canTrade 本身（适配/白名单/交易开关/Boss 开关）已在
 * NeutralizationScopeTest / TradeOfferBuilderTest 覆盖，这里只验组合决策。
 */
class TradeInteractionTest {

    /** 全开基线：可交易、不愤怒、存活、未在交易、空手、有报价 → OPEN。 */
    @Test
    void 条件全开_打开界面() {
        assertEquals(TradeInteraction.Decision.OPEN,
                TradeInteraction.evaluate(true, false, true, true, true, true));
    }

    @Test
    void 不能交易_放行原版() {
        assertEquals(TradeInteraction.Decision.FALL_THROUGH,
                TradeInteraction.evaluate(false, false, true, true, true, true));
    }

    @Test
    void 仇恨中_放行原版() {
        assertEquals(TradeInteraction.Decision.FALL_THROUGH,
                TradeInteraction.evaluate(true, true, true, true, true, true));
    }

    @Test
    void 已死亡_放行原版() {
        assertEquals(TradeInteraction.Decision.FALL_THROUGH,
                TradeInteraction.evaluate(true, false, false, true, true, true));
    }

    @Test
    void 正在被其他玩家交易_不重复开() {
        assertEquals(TradeInteraction.Decision.FALL_THROUGH,
                TradeInteraction.evaluate(true, false, true, false, true, true));
    }

    @Test
    void 主手或副手持物_放行原版交互() {
        // bothHandsEmpty=false 涵盖主手持物、副手持物、双手都持物
        assertEquals(TradeInteraction.Decision.FALL_THROUGH,
                TradeInteraction.evaluate(true, false, true, true, false, true));
    }

    @Test
    void 条件满足但无报价_吞掉交互但不开界面() {
        assertEquals(TradeInteraction.Decision.EMPTY_OFFERS,
                TradeInteraction.evaluate(true, false, true, true, true, false));
    }

    @Test
    void 仇恨优先于报价判定() {
        // 即使没货，仇恨中也必须放行（不吞交互）
        assertEquals(TradeInteraction.Decision.FALL_THROUGH,
                TradeInteraction.evaluate(true, true, true, true, true, false));
    }
}
