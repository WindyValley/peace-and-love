package top.windyvalley.peaceandlove.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonSyntaxException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 配置文件读写与容错。
 *
 * <p>用 GSON（MC 自带，无需额外依赖）。
 *
 * <p>容错策略（对应 T-CFG-002 验收标准，逐条有据）：
 * <ol>
 *   <li><b>首次启动</b>自动生成默认配置</li>
 *   <li><b>字段缺失</b>用默认值补齐并回写</li>
 *   <li><b>JSON 语法错误</b>不崩服，回退全默认 + WARN，且把损坏文件备份为
 *       {@code .broken} 便于管理员排查，而不是直接覆盖丢掉</li>
 *   <li><b>数值越界</b>clamp 到合法范围 + WARN（如 price_max 受 MerchantOffer
 *       双槽限制，最大 128）</li>
 *   <li><b>未知字段</b>保留不丢弃（向前兼容，旧版本配置升级后新字段不丢）</li>
 * </ol>
 */
public final class ConfigLoader {

    private static final Logger LOGGER = LoggerFactory.getLogger("Peace And Love/Config");

    /** price_max 的合法上限：MerchantOffer 双输入槽 64+64。 */
    private static final int PRICE_MAX_LIMIT = 128;

    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();
    private final Path path;

    public ConfigLoader(Path configDir) {
        this.path = configDir.resolve("peaceandlove.json");
    }

    /** 配置文件的完整路径。 */
    public Path path() {
        return path;
    }

    /**
     * 加载配置。
     *
     * <p>文件不存在 → 生成默认并落盘。
     * 语法错误 → 备份损坏文件 + 回退默认（不崩服）。
     * 字段缺失/越界 → 补齐/clamp + 回写。
     */
    public PalConfig load() {
        if (!Files.exists(path)) {
            LOGGER.info("配置文件不存在，生成默认配置: {}", path);
            PalConfig def = PalConfig.defaults();
            save(def);
            return def;
        }

        JsonObject root;
        try (Reader r = Files.newBufferedReader(path)) {
            JsonElement el = JsonParser.parseReader(r);
            if (!el.isJsonObject()) {
                throw new JsonSyntaxException("根节点不是 JSON 对象");
            }
            root = el.getAsJsonObject();
        } catch (JsonSyntaxException | IOException e) {
            return recoverFromBroken(e);
        }

        // 逐字段解析（缺失补齐 + 越界 clamp），并保留未知字段
        ParseResult result = parse(root);

        if (result.dirty) {
            // 有补齐或 clamp，把合并后的完整 JSON（含未知字段）回写
            writeJson(result.merged);
        }
        return result.config;
    }

    /** 保存配置（完整覆盖，含默认格式）。 */
    public void save(PalConfig cfg) {
        writeJson(toJson(cfg));
    }

    // ─────────────────────────── 解析 ───────────────────────────

    private record ParseResult(PalConfig config, JsonObject merged, boolean dirty) {
    }

    private ParseResult parse(JsonObject root) {
        PalConfig def = PalConfig.defaults();
        JsonObject merged = root.deepCopy();
        boolean dirty = false;

        // 生效范围：白名单
        List<String> whitelist = def.hostile_whitelist();
        if (root.has("hostile_whitelist")) {
            whitelist = readStringList(root, "hostile_whitelist", def.hostile_whitelist());
        } else {
            merged.add("hostile_whitelist", gson.toJsonTree(def.hostile_whitelist()));
            dirty = true;
        }

        // 数值字段：缺失补默认、越界 clamp
        double kin_alert_radius = readDouble(root, merged, "kin_alert_radius",
                def.kin_alert_radius(), 0.0, 64.0);
        int anger_cooldown_seconds = readInt(root, merged, "anger_cooldown_seconds",
                def.anger_cooldown_seconds(), 0, 100000);
        double anger_cooldown_distance = readDouble(root, merged, "anger_cooldown_distance",
                def.anger_cooldown_distance(), 1.0, 256.0);

        boolean trading_enabled = readBool(root, merged, "trading_enabled", def.trading_enabled());
        boolean boss_trading_enabled = readBool(root, merged, "boss_trading_enabled",
                def.boss_trading_enabled());
        int max_uses_per_day = readInt(root, merged, "max_uses_per_day",
                def.max_uses_per_day(), 1, 64);
        double restock_interval_days = readDouble(root, merged, "restock_interval_days",
                def.restock_interval_days(), 0.01, 100.0);

        int price_max = readInt(root, merged, "price_max",
                def.price_max(), 1, PRICE_MAX_LIMIT);
        double epk_cheap = readDouble(root, merged, "epk_cheap",
                def.epk_cheap(), 0.0001, 100.0);
        double epk_rare = readDouble(root, merged, "epk_rare",
                def.epk_rare(), 0.000001, 100.0);
        // 交叉校验：两个锚点除各自范围外，还必须满足 cheap > rare（对数曲线的前提）。
        // 二者关系非法时整条曲线无定义，回退默认锚点而不是放进一份会让定价在交易时
        // 才炸的配置（呼应 T-CFG-003「畸形配置不生效/失败保留可用配置」）。
        if (!(epk_cheap > 0d && epk_rare > 0d) || epk_cheap <= epk_rare) {
            LOGGER.warn("定价锚点非法：要求 epk_cheap > epk_rare > 0，当前 epk_cheap={}、epk_rare={}；回退默认 {} / {}",
                    epk_cheap, epk_rare, def.epk_cheap(), def.epk_rare());
            epk_cheap = def.epk_cheap();
            epk_rare = def.epk_rare();
            merged.addProperty("epk_cheap", epk_cheap);
            merged.addProperty("epk_rare", epk_rare);
            dirty = true;
        }

        Map<String, Integer> price_overrides = readOverrides(root, merged, def, dirty);

        // dirty 需综合所有读取结果 —— 上面的 read* 内部已往 merged 补齐
        dirty = dirty || hasAnyMissing(root,
                "kin_alert_radius", "anger_cooldown_seconds", "anger_cooldown_distance",
                "trading_enabled", "boss_trading_enabled", "max_uses_per_day",
                "restock_interval_days", "price_max", "epk_cheap", "epk_rare",
                "price_overrides");

        PalConfig cfg = new PalConfig(
                whitelist,
                kin_alert_radius, anger_cooldown_seconds, anger_cooldown_distance,
                trading_enabled, boss_trading_enabled, max_uses_per_day, restock_interval_days,
                price_max, epk_cheap, epk_rare, price_overrides);
        return new ParseResult(cfg, merged, dirty);
    }

    private boolean hasAnyMissing(JsonObject root, String... keys) {
        for (String k : keys) {
            if (!root.has(k)) {
                return true;
            }
        }
        return false;
    }

    private List<String> readStringList(JsonObject root, String key, List<String> def) {
        try {
            List<String> out = new ArrayList<>();
            for (JsonElement e : root.getAsJsonArray(key)) {
                out.add(e.getAsString());
            }
            return List.copyOf(out);
        } catch (RuntimeException e) {
            LOGGER.warn("字段 {} 不是字符串数组，回退默认", key);
            return def;
        }
    }

    private int readInt(JsonObject root, JsonObject merged, String key,
                        int def, int min, int max) {
        if (!root.has(key)) {
            merged.addProperty(key, def);
            return def;
        }
        int v;
        try {
            v = root.get(key).getAsInt();
        } catch (RuntimeException e) {
            LOGGER.warn("字段 {} 不是整数（{}），回退默认 {}", key, root.get(key), def);
            merged.addProperty(key, def);
            return def;
        }
        if (v < min || v > max) {
            int clamped = Math.max(min, Math.min(max, v));
            LOGGER.warn("字段 {} 越界（{} 不在 [{}, {}]），clamp 为 {}", key, v, min, max, clamped);
            merged.addProperty(key, clamped);
            return clamped;
        }
        return v;
    }

    private double readDouble(JsonObject root, JsonObject merged, String key,
                              double def, double min, double max) {
        if (!root.has(key)) {
            merged.addProperty(key, def);
            return def;
        }
        double v;
        try {
            v = root.get(key).getAsDouble();
        } catch (RuntimeException e) {
            LOGGER.warn("字段 {} 不是数值（{}），回退默认 {}", key, root.get(key), def);
            merged.addProperty(key, def);
            return def;
        }
        if (v < min || v > max) {
            double clamped = Math.max(min, Math.min(max, v));
            LOGGER.warn("字段 {} 越界（{} 不在 [{}, {}]），clamp 为 {}", key, v, min, max, clamped);
            merged.addProperty(key, clamped);
            return clamped;
        }
        return v;
    }

    private boolean readBool(JsonObject root, JsonObject merged, String key, boolean def) {
        if (!root.has(key)) {
            merged.addProperty(key, def);
            return def;
        }
        try {
            return root.get(key).getAsBoolean();
        } catch (RuntimeException e) {
            LOGGER.warn("字段 {} 不是布尔（{}），回退默认 {}", key, root.get(key), def);
            merged.addProperty(key, def);
            return def;
        }
    }

    private Map<String, Integer> readOverrides(JsonObject root, JsonObject merged,
                                               PalConfig def, boolean dirty) {
        if (!root.has("price_overrides")) {
            merged.add("price_overrides", new JsonObject());
            return def.price_overrides();
        }
        try {
            Map<String, Integer> out = new LinkedHashMap<>();
            for (Map.Entry<String, JsonElement> e : root.getAsJsonObject("price_overrides").entrySet()) {
                out.put(e.getKey(), e.getValue().getAsInt());
            }
            return Map.copyOf(out);
        } catch (RuntimeException e) {
            LOGGER.warn("price_overrides 解析失败，回退为空");
            merged.add("price_overrides", new JsonObject());
            return def.price_overrides();
        }
    }

    // ─────────────────────────── 容错回退 ───────────────────────────

    private PalConfig recoverFromBroken(Exception e) {
        LOGGER.warn("配置文件损坏（{}），回退默认配置。原文件备份为 .broken", e.getMessage());
        // 备份损坏文件而不是直接覆盖，便于管理员排查
        try {
            Path broken = path.resolveSibling(path.getFileName() + ".broken");
            Files.copy(path, broken, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            LOGGER.warn("损坏的配置已备份: {}", broken);
        } catch (IOException io) {
            LOGGER.warn("备份损坏配置失败: {}", io.getMessage());
        }
        PalConfig def = PalConfig.defaults();
        save(def);
        return def;
    }

    // ─────────────────────────── 序列化 ───────────────────────────

    private JsonObject toJson(PalConfig c) {
        JsonObject o = new JsonObject();
        o.add("hostile_whitelist", gson.toJsonTree(c.hostile_whitelist()));
        o.addProperty("kin_alert_radius", c.kin_alert_radius());
        o.addProperty("anger_cooldown_seconds", c.anger_cooldown_seconds());
        o.addProperty("anger_cooldown_distance", c.anger_cooldown_distance());
        o.addProperty("trading_enabled", c.trading_enabled());
        o.addProperty("boss_trading_enabled", c.boss_trading_enabled());
        o.addProperty("max_uses_per_day", c.max_uses_per_day());
        o.addProperty("restock_interval_days", c.restock_interval_days());
        o.addProperty("price_max", c.price_max());
        o.addProperty("epk_cheap", c.epk_cheap());
        o.addProperty("epk_rare", c.epk_rare());
        JsonObject ov = new JsonObject();
        c.price_overrides().forEach(ov::addProperty);
        o.add("price_overrides", ov);
        return o;
    }

    private void writeJson(JsonObject o) {
        try {
            Files.createDirectories(path.getParent());
            try (Writer w = Files.newBufferedWriter(path)) {
                gson.toJson(o, w);
            }
        } catch (IOException e) {
            LOGGER.error("写配置文件失败: {}", e.getMessage());
        }
    }
}
