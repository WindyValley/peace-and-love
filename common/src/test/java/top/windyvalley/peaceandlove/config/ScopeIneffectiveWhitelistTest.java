package top.windyvalley.peaceandlove.config;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * T-SCOPE-003：未适配白名单条目的 INFO 提示与去重。
 *
 * <p>日志输出本身（INFO 级、文案）需真机确认；这里验证的是
 * 「同一 id 在两次 reload 间只提示一次」的去重行为 —— 通过
 * ineffectiveNotified 集合的状态断言。
 */
class ScopeIneffectiveWhitelistTest {

    @TempDir
    Path dir;

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    @SuppressWarnings("unchecked")
    private Set<String> notifiedSet(ConfigManager m) throws Exception {
        Field f = ConfigManager.class.getDeclaredField("ineffectiveNotified");
        f.setAccessible(true);
        return (Set<String>) f.get(m);
    }

    @Test
    void 未适配条目初次加载即记录() throws Exception {
        Files.writeString(dir.resolve("peaceandlove.json"),
                "{\"hostile_whitelist\": [\"minecraft:ender_dragon\"]}");
        ConfigManager m = new ConfigManager(dir);
        assertTrue(notifiedSet(m).contains("minecraft:ender_dragon"),
                "初次加载应记录无效条目");
    }

    @Test
    void 同一id两次reload去重不重复记录() throws Exception {
        Files.writeString(dir.resolve("peaceandlove.json"),
                "{\"hostile_whitelist\": [\"minecraft:ender_dragon\"]}");
        ConfigManager m = new ConfigManager(dir);
        m.reload();
        m.reload();
        // 去重集合中该 id 仍只有一个（Set 语义保证，且未因重复提示而膨胀）
        assertEquals(1, notifiedSet(m).size(), "多次 reload 后去重集合不应膨胀");
    }

    @Test
    void 移出白名单后再次加入可重新提示() throws Exception {
        Files.writeString(dir.resolve("peaceandlove.json"),
                "{\"hostile_whitelist\": [\"minecraft:ender_dragon\"]}");
        ConfigManager m = new ConfigManager(dir);
        assertEquals(1, notifiedSet(m).size());

        // 移出后再 reload，去重集合应清空（retainAll）
        m.changeWhitelist("minecraft:ender_dragon", false);
        Files.writeString(dir.resolve("peaceandlove.json"), "{\"hostile_whitelist\": []}");
        m.reload();
        assertEquals(0, notifiedSet(m).size(), "移出白名单后去重集合应清空");
    }

    @Test
    void 有效适配条目不记录() throws Exception {
        Files.writeString(dir.resolve("peaceandlove.json"),
                "{\"hostile_whitelist\": [\"minecraft:zombie\"]}");
        ConfigManager m = new ConfigManager(dir);
        assertEquals(0, notifiedSet(m).size(), "有效条目不应进入无效去重集合");
    }
}
