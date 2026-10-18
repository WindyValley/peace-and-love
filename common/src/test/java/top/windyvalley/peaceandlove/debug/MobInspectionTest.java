package top.windyvalley.peaceandlove.debug;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link MobInspection} 渲染结论的纯 JUnit 覆盖。
 *
 * <p>该 record 不引用 Minecraft 运行时类，故无需 Bootstrap.bootStrap()；
 * 依赖真实 Mob 的字段采集正确性（{@code MobInspector}）移交真机验证。
 * 这里锁定的是「给定一组门控/仇恨字段，回显必须得出正确结论」。
 */
class MobInspectionTest {

    /** 便捷构造：只关心的字段显式给，其余用「一只普通已适配中立怪」的默认值。 */
    private static MobInspection of(boolean adapted, boolean whitelisted, boolean neutralized,
                                   boolean canTrade, boolean angry) {
        return new MobInspection(
                "minecraft:zombie", adapted, whitelisted, false, false, neutralized, canTrade,
                angry, "NONE", false, -1, null, -1, 30, 32);
    }

    private static String joined(MobInspection i) {
        return String.join("\n", i.toLines());
    }

    @Test
    void 未适配生物走短路分支_提示保持原版() {
        MobInspection i = of(false, false, false, false, false);
        String text = joined(i);
        assertTrue(text.contains("未适配"), "应显示未适配: " + text);
        assertTrue(text.contains("保持原版"), "应说明行为保持原版");
        assertTrue(text.contains("不可"), "未适配不可交易");
        // 短路：不应再出现门控链其余字段
        assertFalse(text.contains("白名单: §a否"), "未适配时不应渲染白名单行");
    }

    @Test
    void 已适配未在白名单_中立可交易_无仇恨() {
        MobInspection i = of(true, false, true, true, false);
        String text = joined(i);
        assertTrue(text.contains("中立化: §a是"));
        assertTrue(text.contains("可交易: §a是"));
        assertTrue(text.contains("白名单: §a否"));
        assertTrue(text.contains("仇恨: §a无"));
    }

    @Test
    void 已适配但在白名单_不中立不可交易() {
        MobInspection i = of(true, true, false, false, false);
        String text = joined(i);
        assertTrue(text.contains("白名单: §c是（保持原版敌对）"));
        assertTrue(text.contains("中立化: §c否"));
        assertTrue(text.contains("可交易: §c否"));
    }

    @Test
    void 愤怒且有倒计时_显示来源与剩余秒数() {
        MobInspection i = new MobInspection(
                "minecraft:zombie", true, false, false, false, true, false,
                true, "玩家直接攻击", false, 12.5, null, -1, 30, 32);
        String text = joined(i);
        assertTrue(text.contains("仇恨: §c玩家直接攻击"), text);
        assertTrue(text.contains("剩余 §f12.5s"), "应显示剩余秒数: " + text);
        assertTrue(text.contains("冷却 30s"));
        assertTrue(text.contains("脱战距离 32 格"));
    }

    @Test
    void 永久仇恨_显示永久且不显示倒计时() {
        MobInspection i = new MobInspection(
                "minecraft:warden", true, false, true, true, true, false,
                true, "同族示警", true, -1, null, -1, 0, 32);
        String text = joined(i);
        assertTrue(text.contains("永久"), text);
        assertFalse(text.contains("剩余 §f"), "永久仇恨不显示剩余秒数");
    }

    @Test
    void 有目标时_显示目标描述与距离() {
        MobInspection i = new MobInspection(
                "minecraft:zombie", true, false, false, false, true, true,
                true, "玩家直接攻击", false, 20, "玩家 Dev", 4.0, 30, 32);
        List<String> lines = i.toLines();
        String targetLine = lines.stream().filter(l -> l.contains("当前目标")).findFirst().orElseThrow();
        assertTrue(targetLine.contains("玩家 Dev"), targetLine);
        assertTrue(targetLine.contains("距离 §f4"), targetLine);
    }

    @Test
    void 无目标时_显示无目标() {
        MobInspection i = of(true, false, true, true, false);
        assertTrue(joined(i).contains("当前目标: §7无"));
    }

    @Test
    void 数字格式化_整数不带小数_非整数一位() {
        assertEquals("32", MobInspection.fmtNum(32.0));
        assertEquals("4", MobInspection.fmtNum(4.0));
        assertEquals("12.5", MobInspection.fmtNum(12.5));
        assertEquals("0", MobInspection.fmtNum(0.0));
    }

    @Test
    void brain系与boss标签体现在标题() {
        MobInspection i = new MobInspection(
                "minecraft:warden", true, false, true, true, true, false,
                false, "NONE", false, -1, null, -1, 30, 32);
        String title = i.toLines().get(0);
        assertTrue(title.contains("Brain 系"), title);
        assertTrue(title.contains("Boss"), title);
        assertTrue(title.contains("minecraft:warden"));
    }

    @Test
    void toMap_字段与record组件一一对应且key稳定() {
        MobInspection i = new MobInspection(
                "minecraft:warden", true, false, true, true, true, false,
                true, "同族示警", false, 12.5, "玩家 Dev", 4.0, 30, 32);
        var m = i.toMap();
        assertEquals("minecraft:warden", m.get("entityId"));
        assertEquals(Boolean.TRUE, m.get("adapted"));
        assertEquals(Boolean.FALSE, m.get("whitelisted"));
        assertEquals(Boolean.TRUE, m.get("brainBased"));
        assertEquals(Boolean.TRUE, m.get("boss"));
        assertEquals(Boolean.TRUE, m.get("neutralized"));
        assertEquals(Boolean.FALSE, m.get("canTrade"));
        assertEquals(Boolean.TRUE, m.get("angry"));
        assertEquals("同族示警", m.get("angerSource"));
        assertEquals(Boolean.FALSE, m.get("angerPermanent"));
        assertEquals(12.5, m.get("remainingAngerSeconds"));
        assertEquals("玩家 Dev", m.get("targetDescription"));
        assertEquals(4.0, m.get("targetDistance"));
        assertEquals(30.0, m.get("cooldownSeconds"));
        assertEquals(32.0, m.get("cooldownDistance"));
        // 15 个字段全覆盖
        assertEquals(15, m.size(), m.keySet().toString());
    }

    @Test
    void toMap_无目标时targetDescription归一空串而非null() {
        // Gson 默认丢弃 null 值，探针 JSON 会少 key；契约要求无目标给空串，key 集合恒定。
        MobInspection i = new MobInspection(
                "minecraft:zombie", true, false, false, false, true, true,
                false, "NONE", false, -1, null, -1, 30, 32);
        var m = i.toMap();
        assertEquals("", m.get("targetDescription"));
        assertEquals(15, m.size(), m.keySet().toString());
    }
}
