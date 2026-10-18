package top.windyvalley.peaceandlove.debug;

import java.util.ArrayList;
import java.util.List;

/**
 * {@code /pal inspect} 单只生物的诊断快照与纯文本渲染。
 *
 * <p>本 record 只持有基本类型与 String，<b>不引用任何 Minecraft 运行时类</b>，
 * 因此 {@link #toLines()} 的渲染结论可以纯 JUnit 覆盖。从真实 Mob 采集这些
 * 字段是 {@link MobInspector} 的职责（依赖服务端运行时，真机验证）。
 *
 * <p>字段刻意覆盖两条最容易出问题的链路：
 * <ol>
 *   <li><b>门控链</b>：adapted → whitelisted → neutralized → canTrade，
 *       出问题时一眼能看出是「没适配」还是「被白名单排除」还是「交易开关关了」。</li>
 *   <li><b>仇恨链</b>：angry / angerSource / 剩余时间 / 当前目标与距离，
 *       配合冷却配置就能判断「为什么还在追」或「为什么脱战了」。</li>
 * </ol>
 *
 * @param entityId              注册名，如 {@code minecraft:zombie}
 * @param adapted               是否在已适配清单（代码能力边界）
 * @param whitelisted          是否在白名单（已适配但保持原版）
 * @param brainBased            是否走 Brain AI（否则走 Goal）
 * @param boss                  是否为需额外交易开关的 Boss（凋灵/监守者）
 * @param neutralized           是否实际被中立化（adapted AND !whitelisted）
 * @param canTrade              当前能否交易
 * @param angry                 当前是否处于对玩家的仇恨状态
 * @param angerSource           仇恨来源名（NONE/PLAYER_DIRECT/KIN_ALERT/原版NeutralMob）
 * @param angerPermanent        仇恨是否永久（冷却配置为 0）
 * @param remainingAngerSeconds 剩余仇恨秒数；&lt;0 表示无可显示的倒计时（含未愤怒）
 * @param targetDescription     当前攻击目标的描述；{@code null} 表示无目标
 * @param targetDistance        与当前目标的距离（格）；&lt;0 表示无目标
 * @param cooldownSeconds       配置的脱战冷却秒数（0=永久）
 * @param cooldownDistance      配置的脱战距离（格）
 */
public record MobInspection(
        String entityId,
        boolean adapted,
        boolean whitelisted,
        boolean brainBased,
        boolean boss,
        boolean neutralized,
        boolean canTrade,
        boolean angry,
        String angerSource,
        boolean angerPermanent,
        double remainingAngerSeconds,
        String targetDescription,
        double targetDistance,
        double cooldownSeconds,
        double cooldownDistance
) {

    /**
     * 渲染为多行中文诊断文本（不含颜色前缀之外的任何运行时依赖）。
     *
     * <p>颜色用原版 section 记号：{@code §a} 绿 / {@code §c} 红 / {@code §e} 黄 /
     * {@code §7} 灰。命令层逐行包成 {@code Component.literal} 回显。
     */
    public List<String> toLines() {
        List<String> lines = new ArrayList<>();
        lines.add("§6[PAL] §f" + entityId
                + " §7[" + (brainBased ? "Brain 系" : "Goal 系")
                + (boss ? " · Boss" : "") + "]");

        // ── 门控链 ──
        if (!adapted) {
            lines.add("  §7适配: §c未适配 §7— 行为完全保持原版（mod 生物同样如此）");
            lines.add("  §7交易: §7不可（未适配生物不在交易范围内）");
            lines.add("  §7仇恨: §7" + (angry ? "当前有目标（原版机制，本 mod 不干预）" : "无目标"));
            appendTarget(lines);
            return lines;
        }

        lines.add("  §7适配: §a已适配");
        lines.add("  §7白名单: " + (whitelisted ? "§c是（保持原版敌对）" : "§a否"));
        lines.add("  §7中立化: " + (neutralized ? "§a是" : "§c否"));
        lines.add("  §7可交易: " + (canTrade ? "§a是" : "§c否"));

        // ── 仇恨链 ──
        if (!angry) {
            lines.add("  §7仇恨: §a无 §7（中立，可被攻击前不会主动攻击玩家）");
        } else {
            StringBuilder sb = new StringBuilder("  §7仇恨: §c")
                    .append(angerSource == null ? "UNKNOWN" : angerSource);
            if (angerPermanent) {
                sb.append(" §7（永久，冷却配置为 0）");
            } else if (remainingAngerSeconds >= 0) {
                sb.append(" §7剩余 §f").append(String.format("%.1f", remainingAngerSeconds)).append("s");
            }
            sb.append(" §7冷却 ").append(fmtNum(cooldownSeconds)).append("s")
              .append(" / 脱战距离 ").append(fmtNum(cooldownDistance)).append(" 格");
            lines.add(sb.toString());
        }
        appendTarget(lines);
        return lines;
    }

    private void appendTarget(List<String> lines) {
        if (targetDescription == null) {
            lines.add("  §7当前目标: §7无");
            return;
        }
        String dist = targetDistance >= 0
                ? " §7距离 §f" + fmtNum(targetDistance) + " §7格" : "";
        lines.add("  §7当前目标: §e" + targetDescription + dist);
    }

    /** 整数不带小数点（32.0 → 32），非整数保留一位。 */
    static String fmtNum(double v) {
        if (v == Math.rint(v)) {
            return Long.toString((long) v);
        }
        return String.format("%.1f", v);
    }

    /**
     * 转成结构化 Map，供 verify-RPC 探针序列化成 JSON（真机脚本断言采集层用）。
     *
     * <p>字段与 record 组件一一对应，仍是纯基本类型/String，不引入 MC 运行时依赖。
     * key 用稳定 snake_case，作为探针 {@code debug.inspect} 的对外契约。
     */
    public java.util.Map<String, Object> toMap() {
        java.util.Map<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("entityId", entityId);
        m.put("adapted", adapted);
        m.put("whitelisted", whitelisted);
        m.put("brainBased", brainBased);
        m.put("boss", boss);
        m.put("neutralized", neutralized);
        m.put("canTrade", canTrade);
        m.put("angry", angry);
        m.put("angerSource", angerSource);
        m.put("angerPermanent", angerPermanent);
        m.put("remainingAngerSeconds", remainingAngerSeconds);
        // Gson 默认不序列化 null（key 会整个消失）。无目标时归一成空串而非 null，
        // 保证 debug.inspect 的 JSON key 集合在有/无目标下一致，脚本可稳定下标。
        m.put("targetDescription", targetDescription == null ? "" : targetDescription);
        m.put("targetDistance", targetDistance);
        m.put("cooldownSeconds", cooldownSeconds);
        m.put("cooldownDistance", cooldownDistance);
        return m;
    }
}
