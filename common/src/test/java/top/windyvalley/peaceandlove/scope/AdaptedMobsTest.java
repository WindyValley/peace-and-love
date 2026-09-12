package top.windyvalley.peaceandlove.scope;

import net.minecraft.world.entity.EntityType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 已适配生物清单测试。
 *
 * <p>清单由 neutralization_plan_v3.json 生成（勿手改），这里的断言
 * 锁死的是设计文档的口径，与生成逻辑互相印证。
 *
 * <p>引用 EntityType 常量会触发其 &lt;clinit&gt;，进而要求注册表已
 * bootstrap。纯 JUnit 没有这个环境，必须先手动引导，否则
 * ExceptionInInitializerError。
 */
class AdaptedMobsTest {

    @BeforeAll
    static void bootstrap() {
        // 引导 MC 注册表，让 EntityType.<clinit> 能正常执行。
        // 顺序不能反：先 detectVersion 再 bootStrap。
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    @Test
    void 总数为38() {
        assertEquals(38, AdaptedMobs.count(), "GOAL(32) + BRAIN(6) = 38");
    }

    @Test
    void Goal系32个() {
        assertEquals(32, AdaptedMobs.GOAL_BASED.size());
    }

    @Test
    void Brain系6个() {
        assertEquals(6, AdaptedMobs.BRAIN_BASED.size());
    }

    @Test
    void Brain系内容() {
        Set<EntityType<?>> b = AdaptedMobs.BRAIN_BASED;
        assertTrue(b.contains(EntityType.PIGLIN),       "猪灵");
        assertTrue(b.contains(EntityType.PIGLIN_BRUTE), "猪灵蛮兵");
        assertTrue(b.contains(EntityType.HOGLIN),       "疣猪兽");
        assertTrue(b.contains(EntityType.ZOGLIN),       "僵尸疣猪兽");
        assertTrue(b.contains(EntityType.WARDEN),       "监守者");
        assertTrue(b.contains(EntityType.BREEZE),       "旋风人");
    }

    @Test
    void 两组无交集() {
        for (EntityType<?> t : AdaptedMobs.GOAL_BASED) {
            assertFalse(AdaptedMobs.BRAIN_BASED.contains(t),
                    "不应同时属于两组: " + t);
        }
    }

    @Test
    void 末影龙不在列表() {
        // v1.0 不适配，行为完全不变。这是设计明确排除项，曾被遗漏进 JSON。
        assertFalse(AdaptedMobs.isAdapted(EntityType.ENDER_DRAGON),
                "末影龙 v1.1 才适配，v1.0 不应在已适配列表");
    }

    @Test
    void 凋灵在列表() {
        // 凋灵已适配（默认中立化），只是 boss_trading_enabled=false 时不开交易。
        assertTrue(AdaptedMobs.isAdapted(EntityType.WITHER),
                "凋灵已适配，应在列表中");
    }

    @Test
    void 动物不在列表() {
        // 已适配列表只含敌对生物。动物天然不受影响 —— 这是模组免疫第三方
        // 生物的机制基础，不是靠白名单实现的。
        assertFalse(AdaptedMobs.isAdapted(EntityType.COW), "牛不应在列表");
        assertFalse(AdaptedMobs.isAdapted(EntityType.VILLAGER), "村民不应在列表");
    }

    @Test
    void 集合不可变() {
        assertThrows(UnsupportedOperationException.class,
                () -> AdaptedMobs.GOAL_BASED.add(EntityType.ENDER_DRAGON));
        assertThrows(UnsupportedOperationException.class,
                () -> AdaptedMobs.ALL.add(EntityType.ENDER_DRAGON));
    }
}
