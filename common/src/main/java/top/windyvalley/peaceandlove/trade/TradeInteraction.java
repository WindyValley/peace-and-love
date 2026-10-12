package top.windyvalley.peaceandlove.trade;

/**
 * 右键交易交互的门控决策（T-TRADE-003）—— 纯逻辑，不依赖 Mob 实例，可直接单测。
 *
 * <p>Mixin 只负责从 Mob/Player 抽取事实再调用 {@link #evaluate}，
 * 真值表全部收敛在这里，避免把判定散进 Mixin 无法覆盖。
 *
 * <p>决策语义：
 * <ul>
 *   <li>{@link Decision#FALL_THROUGH} —— 不拦截，交给原版 mobInteract
 *       （未适配/白名单/开关关/Boss 开关关、仇恨中、死亡、已在交易、手持物品）；</li>
 *   <li>{@link Decision#EMPTY_OFFERS} —— 条件满足但没有可售报价，
 *       吞掉交互（服务端 CONSUME）但不开界面，对齐原版村民「没货」行为；</li>
 *   <li>{@link Decision#OPEN} —— 打开原版交易 GUI。
 *       客户端只做挥手预测（SUCCESS），真正开界面由服务端 openTradingScreen 发包。</li>
 * </ul>
 */
public final class TradeInteraction {

    public enum Decision {
        /** 不拦截，保持原版交互。 */
        FALL_THROUGH,
        /** 吞掉右键但不开界面（无可售报价）。 */
        EMPTY_OFFERS,
        /** 打开交易界面（服务端）/挥手预测（客户端）。 */
        OPEN
    }

    private TradeInteraction() {
    }

    /**
     * @param canTrade        {@code NeutralizationScope.canTrade}（已含适配/白名单/交易开关/Boss 开关）
     * @param angry           生物当前是否处于对玩家的仇恨状态（AngerController.isAngry）
     * @param alive           生物存活
     * @param notTrading      当前没有其他玩家正在与它交易
     * @param bothHandsEmpty  玩家主手+副手都为空（空手才触发，持物保留原版交互）
     * @param hasOffers       组装出的报价单非空
     */
    public static Decision evaluate(boolean canTrade, boolean angry, boolean alive,
                                    boolean notTrading, boolean bothHandsEmpty,
                                    boolean hasOffers) {
        if (!canTrade || angry || !alive || !notTrading || !bothHandsEmpty) {
            return Decision.FALL_THROUGH;
        }
        return hasOffers ? Decision.OPEN : Decision.EMPTY_OFFERS;
    }
}
