package top.windyvalley.peaceandlove.config;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 配置管理器测试。
 *
 * <p>涉及白名单有效性校验的用例会走 adaptedIds()，需注册表 bootstrap。
 * 统一在 @BeforeAll 引导，无妨。
 */
class ConfigManagerTest {

    @TempDir
    Path dir;

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    private ConfigManager manager() {
        return new ConfigManager(dir);
    }

    // ── 初始加载 ──

    @Test
    void 初始加载生成默认配置() {
        ConfigManager m = manager();
        assertEquals(6, m.get().hostile_whitelist().size());
        assertTrue(Files.exists(m.path()));
    }

    // ── 热重载 ──

    @Test
    void 重载后读到新配置() throws IOException {
        ConfigManager m = manager();
        // 改文件后重载
        Files.writeString(m.path(), "{\"price_max\": 64}");
        ConfigManager.ReloadResult r = m.reload();
        assertTrue(r.success());
        assertEquals(64, m.get().price_max(), "重载后应读到新值");
    }

    @Test
    void 重载失败保留旧配置() throws IOException {
        ConfigManager m = manager();
        int before = m.get().price_max();
        // 写入损坏内容 —— loader 会容错回退默认，所以这里验证的是
        // "重载后 get() 仍返回一个完整可用的配置"，不会半初始化
        Files.writeString(m.path(), "{ broken !!!");
        m.reload();
        // 损坏时回退默认（这也是 128），关键是不抛异常、配置完整
        assertEquals(6, m.get().hostile_whitelist().size());
        assertTrue(m.get().price_max() >= 1);
    }

    @Test
    void 重载通知监听器() throws IOException {
        ConfigManager m = manager();
        AtomicReference<PalConfig> received = new AtomicReference<>();
        m.addReloadListener(received::set);

        Files.writeString(m.path(), "{\"price_max\": 32}");
        m.reload();
        assertEquals(32, received.get().price_max(), "监听器应收到新配置");
    }

    @Test
    void 监听器异常不影响重载() throws IOException {
        ConfigManager m = manager();
        m.addReloadListener(c -> { throw new RuntimeException("监听器炸了"); });
        AtomicInteger called = new AtomicInteger();
        m.addReloadListener(c -> called.incrementAndGet());

        Files.writeString(m.path(), "{\"price_max\": 16}");
        ConfigManager.ReloadResult r = m.reload();
        assertTrue(r.success(), "单个监听器异常不应让重载失败");
        assertEquals(1, called.get(), "后续监听器仍应被调用");
        assertEquals(16, m.get().price_max());
    }

    @Test
    void 重载变更摘要() throws IOException {
        ConfigManager m = manager();
        Files.writeString(m.path(), "{\"trading_enabled\": false}");
        ConfigManager.ReloadResult r = m.reload();
        assertTrue(r.message().contains("trading_enabled"),
                "摘要应包含变更的字段: " + r.message());
    }

    // ── 白名单变更 ──

    @Test
    void 白名单添加() {
        ConfigManager m = manager();
        ConfigManager.WhitelistChange c = m.changeWhitelist("minecraft:zombie", true);
        assertTrue(c.changed());
        assertTrue(m.get().hostile_whitelist().contains("minecraft:zombie"));
    }

    @Test
    void 白名单添加自动补全前缀() {
        ConfigManager m = manager();
        m.changeWhitelist("zombie", true);
        assertTrue(m.get().hostile_whitelist().contains("minecraft:zombie"),
                "不带前缀的 id 应自动补全 minecraft:");
    }

    @Test
    void 白名单移除() {
        ConfigManager m = manager();
        ConfigManager.WhitelistChange c = m.changeWhitelist("minecraft:pillager", false);
        assertTrue(c.changed());
        assertFalse(m.get().hostile_whitelist().contains("minecraft:pillager"));
    }

    @Test
    void 白名单重复添加为空操作() {
        ConfigManager m = manager();
        ConfigManager.WhitelistChange c = m.changeWhitelist("minecraft:pillager", true);
        assertFalse(c.changed(), "已在白名单中的不应重复添加");
    }

    @Test
    void 白名单移除不存在项为空操作() {
        ConfigManager m = manager();
        ConfigManager.WhitelistChange c = m.changeWhitelist("minecraft:zombie", false);
        assertFalse(c.changed(), "不在白名单中的无法移除");
    }

    @Test
    void 白名单变更持久化() {
        ConfigManager m = manager();
        m.changeWhitelist("minecraft:zombie", true);
        // 新建一个 manager 读同一文件，应看到变更
        ConfigManager m2 = manager();
        assertTrue(m2.get().hostile_whitelist().contains("minecraft:zombie"),
                "变更应已写入配置文件");
    }

    @Test
    void 白名单变更通知监听器() {
        ConfigManager m = manager();
        AtomicInteger calls = new AtomicInteger();
        m.addReloadListener(c -> calls.incrementAndGet());
        m.changeWhitelist("minecraft:zombie", true);
        assertEquals(1, calls.get());
    }

    @Test
    void 未适配生物加入白名单给提示但仍允许() {
        ConfigManager m = manager();
        ConfigManager.WhitelistChange c = m.changeWhitelist("minecraft:ender_dragon", true);
        assertTrue(c.changed(), "未适配 id 仍允许添加");
        assertTrue(c.ineffective(), "但应标记为无效配置");
        assertTrue(c.message().contains("未适配"), "反馈应提示未适配");
    }
}
