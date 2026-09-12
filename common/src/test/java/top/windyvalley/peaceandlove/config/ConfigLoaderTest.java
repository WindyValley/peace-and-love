package top.windyvalley.peaceandlove.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 配置读写与容错测试。
 *
 * <p>每条用例对应 T-CFG-002 验收标准。GSON 是纯库不碰 MC 注册表，
 * 无需 bootstrap。
 */
class ConfigLoaderTest {

    @TempDir
    Path dir;

    private ConfigLoader loader() {
        return new ConfigLoader(dir);
    }

    private Path file() {
        return dir.resolve("peaceandlove.json");
    }

    @Test
    void 首次启动生成默认配置() {
        PalConfig c = loader().load();
        assertTrue(Files.exists(file()), "应自动生成配置文件");
        assertEquals(PalConfig.defaults().hostile_whitelist(), c.hostile_whitelist());
        assertEquals(128, c.price_max());
    }

    @Test
    void 字段缺失用默认补齐并回写() throws IOException {
        // 只写一个字段，其余全缺
        Files.writeString(file(), "{\"trading_enabled\": false}");
        PalConfig c = loader().load();

        assertFalse(c.trading_enabled(), "已有字段保留原值");
        assertEquals(128, c.price_max(), "缺失字段补默认");
        assertEquals(6, c.hostile_whitelist().size(), "缺失白名单补默认 6 项");

        // 回写后文件应包含补齐的字段
        String json = Files.readString(file());
        assertTrue(json.contains("price_max"), "回写应包含补齐的字段");
        assertTrue(json.contains("hostile_whitelist"), "回写应包含白名单");
    }

    @Test
    void 语法错误不崩服回退默认() throws IOException {
        Files.writeString(file(), "{ this is not valid json !!!");
        PalConfig c = loader().load();
        // 不抛异常即"不崩服"，且回退默认
        assertEquals(PalConfig.defaults().price_max(), c.price_max());
        assertEquals(6, c.hostile_whitelist().size());
    }

    @Test
    void 语法错误时备份损坏文件() throws IOException {
        Files.writeString(file(), "{ broken !!!");
        loader().load();
        Path broken = dir.resolve("peaceandlove.json.broken");
        assertTrue(Files.exists(broken), "损坏文件应备份为 .broken 而不是直接覆盖");
        // 原文件已被默认配置覆盖（可读）
        PalConfig c = loader().load();
        assertEquals(128, c.price_max());
    }

    @Test
    void 非对象根节点视为损坏() throws IOException {
        Files.writeString(file(), "[1,2,3]");
        PalConfig c = loader().load();
        assertEquals(PalConfig.defaults().price_max(), c.price_max());
    }

    @Test
    void 数值越界clamp() throws IOException {
        Files.writeString(file(), "{\"price_max\": 99999}");
        PalConfig c = loader().load();
        assertEquals(128, c.price_max(), "price_max 越界应 clamp 到 128");
    }

    @Test
    void 数值越界下限clamp() throws IOException {
        Files.writeString(file(), "{\"price_max\": -5}");
        PalConfig c = loader().load();
        assertEquals(1, c.price_max(), "price_max 下限 clamp 到 1");
    }

    @Test
    void 未知字段保留不丢弃() throws IOException {
        // 模拟旧版本配置带了一个新版本不认识的字段
        Files.writeString(file(),
                "{\"price_max\": 100, \"future_new_field\": \"keep-me\"}");
        loader().load();
        String json = Files.readString(file());
        assertTrue(json.contains("future_new_field"), "未知字段应保留（向前兼容）");
        assertTrue(json.contains("keep-me"), "未知字段的值应保留");
    }

    @Test
    void 类型错误回退该字段默认() throws IOException {
        Files.writeString(file(), "{\"price_max\": \"not-a-number\"}");
        PalConfig c = loader().load();
        assertEquals(128, c.price_max(), "类型错误回退默认");
    }

    @Test
    void 白名单自定义生效() throws IOException {
        Files.writeString(file(), "{\"hostile_whitelist\": [\"minecraft:zombie\"]}");
        PalConfig c = loader().load();
        assertEquals(List.of("minecraft:zombie"), c.hostile_whitelist());
    }

    @Test
    void 手工定价修正解析() throws IOException {
        Files.writeString(file(),
                "{\"price_overrides\": {\"minecraft:zombie/minecraft:iron_ingot\": 100}}");
        PalConfig c = loader().load();
        assertEquals(Map.of("minecraft:zombie/minecraft:iron_ingot", 100), c.price_overrides());
    }

    @Test
    void 保存后能被完整读回() {
        ConfigLoader l = loader();
        PalConfig original = PalConfig.defaults();
        l.save(original);
        PalConfig read = l.load();
        assertEquals(original, read, "save 后 load 应还原同一配置");
    }
}
