package top.windyvalley.peaceandlove.anger;

/**
 * 仇恨来源 —— 生物当前敌意的归因（设计 docs/02-design.md §3.6）。
 *
 * <p>用于「脱战后能否恢复中立/交易」与「示警是否再传播」的判定，
 * 也服务于 {@code /pal debug anger} 的可观测性。
 */
public enum AngerSource {
    /** 中立，可交易。 */
    NONE,
    /** 被玩家直接/间接攻击 —— 唯一的主动触发源（ADR-004 决策三）。 */
    PLAYER_DIRECT,
    /** 同族示警被激怒（不再向外传播，见 KinAlerter）。 */
    KIN_ALERT
}
