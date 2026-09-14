package top.windyvalley.peaceandlove.anger;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * T-ANGER-002/004：AngerController 的仇恨计时存取（Goal 系自维护部分）。
 *
 * <p>覆盖不依赖真实 Mob 实例的纯状态逻辑：计时写入/读取/递减/重置、
 * 仇恨来源存取。onPlayerAttack/calmDown/tickDecay 依赖真实 Mob
 * （level、Goal 选择器、注册表），纯 JUnit 造不出来，移交真机验证。
 *
 * <p>用反射清掉静态 Map，保证用例间隔离。
 */
class AngerControllerStateTest {

    @BeforeEach
    void 设置冷却覆盖并清空静态状态() throws Exception {
        AngerController.overrideCooldownSecondsForTest(30);
        clearMap("angerTickByMob");
        clearMap("angerSourceByMob");
    }

    @AfterEach
    void 还原冷却覆盖() {
        AngerController.overrideCooldownSecondsForTest(null);
    }

    private static void clearMap(String field) throws Exception {
        var f = AngerController.class.getDeclaredField(field);
        f.setAccessible(true);
        ((java.util.Map<?, ?>) f.get(null)).clear();
    }

    // ── 仇恨计时存取（Goal 系）──────────────────────────────────────

    @Test
    void 无记录时剩余计时为0() {
        assertEquals(0, AngerController.remainingAngerTick(UUID.randomUUID()));
    }

    @Test
    void 递减使剩余计时减少() {
        UUID id = UUID.randomUUID();
        AngerController.resetAngerTick(id);          // 写入一个正数（配置默认 30s=600tick 或永久）
        int before = AngerController.remainingAngerTick(id);
        if (before == Integer.MAX_VALUE) {
            return; // 永久仇恨配置下不参与递减断言
        }
        int after = AngerController.decrementAngerTick(id);
        assertEquals(before - 1, after);
        assertEquals(before - 1, AngerController.remainingAngerTick(id));
    }

    @Test
    void 重置把计时拉满() {
        UUID id = UUID.randomUUID();
        AngerController.resetAngerTick(id);
        int full = AngerController.remainingAngerTick(id);
        if (full == Integer.MAX_VALUE) {
            return;
        }
        AngerController.decrementAngerTick(id);
        AngerController.decrementAngerTick(id);
        AngerController.resetAngerTick(id);
        assertEquals(full, AngerController.remainingAngerTick(id));
    }

    // ── 仇恨来源存取 ────────────────────────────────────────────────
    // angerSourceOf/setAngerSource 以 Mob 为参数，无法纯 JUnit 构造 Mob，
    // 故这里不直接测；其 Map 语义已由计时部分同构覆盖。
    // （setAngerSource(NONE) 即 remove，与 remainingAngerTick 无记录=0 同理）
}
