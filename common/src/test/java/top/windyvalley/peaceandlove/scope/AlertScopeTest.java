package top.windyvalley.peaceandlove.scope;

import net.minecraft.world.entity.EntityType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * AlertScope A/B/C 三分类的结构约束。
 *
 * <p>分类是同族示警重构的地基（Mixin 收窄 / B 置 flag / C 直调三条路径都靠它分派），
 * 必须保证：三类互不相交、计数与「Goal 系已适配总数」一致、各类代表成员归属正确。
 *
 * <p>真机行为（示警是否实际触发）由 verify_alert_* 脚本覆盖，这里只锁结构不变量。
 */
class AlertScopeTest {

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    @Test
    void 三类计数符合设计值() {
        assertEquals(15, AlertScope.NATIVE_ALERT.size(), "A 类（原生示警）");
        assertEquals(10, AlertScope.ENABLE_ALERT_FLAG.size(), "B 类（开 flag）");
        assertEquals(7, AlertScope.DIRECT_ALERT.size(), "C 类（直调）");
    }

    @Test
    void 三类互不相交() {
        Set<EntityType<?>> a = AlertScope.NATIVE_ALERT;
        Set<EntityType<?>> b = AlertScope.ENABLE_ALERT_FLAG;
        Set<EntityType<?>> c = AlertScope.DIRECT_ALERT;
        assertTrue(disjoint(a, b), "A∩B 必须为空");
        assertTrue(disjoint(a, c), "A∩C 必须为空");
        assertTrue(disjoint(b, c), "B∩C 必须为空");
    }

    @Test
    void 并集恰为Goal系已适配集合() {
        Set<EntityType<?>> union = new HashSet<>();
        union.addAll(AlertScope.NATIVE_ALERT);
        union.addAll(AlertScope.ENABLE_ALERT_FLAG);
        union.addAll(AlertScope.DIRECT_ALERT);
        assertEquals(32, union.size(), "合计 32");
        assertEquals(AdaptedMobs.GOAL_BASED, union,
                "每个 Goal 系已适配生物必须且只能归入 A/B/C 之一");
    }

    @Test
    void 代表成员归属正确() {
        // A：原生示警
        assertTrue(AlertScope.NATIVE_ALERT.contains(EntityType.ZOMBIE));
        assertTrue(AlertScope.NATIVE_ALERT.contains(EntityType.PILLAGER));
        // B：有 HurtBy 但无 setAlertOthers
        assertTrue(AlertScope.ENABLE_ALERT_FLAG.contains(EntityType.SKELETON));
        assertTrue(AlertScope.ENABLE_ALERT_FLAG.contains(EntityType.ENDERMAN));
        // C：无 HurtBy
        assertTrue(AlertScope.DIRECT_ALERT.contains(EntityType.GUARDIAN));
        assertTrue(AlertScope.DIRECT_ALERT.contains(EntityType.SLIME));
    }

    @Test
    void 谓词语义与分类一致() {
        assertTrue(AlertScope.requiresDirectAlert(EntityType.GUARDIAN), "guardian 走直调");
        assertTrue(AlertScope.requiresDirectAlert(EntityType.PHANTOM), "phantom 走直调");
        assertFalse(AlertScope.requiresDirectAlert(EntityType.ZOMBIE), "zombie 走 Mixin 收窄");
        assertFalse(AlertScope.requiresDirectAlert(EntityType.SKELETON), "skeleton 走 flag+Mixin");

        assertTrue(AlertScope.isModEnabledAlert(EntityType.SKELETON), "skeleton 是 B 类");
        assertFalse(AlertScope.isModEnabledAlert(EntityType.ZOMBIE), "zombie 不是 B 类");
        assertFalse(AlertScope.isModEnabledAlert(EntityType.SLIME), "slime 是 C 类不是 B 类");
    }

    private static boolean disjoint(Set<?> x, Set<?> y) {
        Set<?> both = new HashSet<>(x);
        return both.stream().noneMatch(y::contains);
    }
}
