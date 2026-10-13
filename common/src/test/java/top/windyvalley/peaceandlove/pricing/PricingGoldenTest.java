package top.windyvalley.peaceandlove.pricing;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 定价黄金基准（T-TEST-001）：Java 实现必须复现 spike 产出的
 * {@code final_pricing_128.json} 全量数值，零误差。
 *
 * <p>该 JSON 由 Gradle 在 processTestResources 时从
 * {@code spikes/design-verify/} 复制为测试资源 {@code golden/final_pricing_128.json}，
 * 单一真相留在 spike，不在测试树里存副本。基准同时带 price_64/price_128 两列，
 * 可顺带验证改 {@code price_max} 后全量仍一致且单调。
 */
class PricingGoldenTest {

    private static final double CHEAP = 2.0;
    private static final double RARE = 0.005;

    private record Row(String entity, String item, double epk,
                       int price64, int price128) {
    }

    private static List<Row> rows;
    private static JsonObject root;

    @BeforeAll
    static void loadGolden() {
        try (InputStream in = PricingGoldenTest.class.getResourceAsStream(
                "/golden/final_pricing_128.json")) {
            Objects.requireNonNull(in, "缺少黄金基准资源 golden/final_pricing_128.json"
                    + "（应由 common/build.gradle 的 copyGoldenPricing 复制）");
            root = JsonParser.parseReader(
                    new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
        } catch (Exception e) {
            throw new ExceptionInInitializerError(e);
        }
        JsonArray arr = root.getAsJsonArray("entries");
        rows = new ArrayList<>(arr.size());
        for (JsonElement el : arr) {
            JsonObject o = el.getAsJsonObject();
            rows.add(new Row(
                    o.get("entity").getAsString(),
                    o.get("item").getAsString(),
                    o.get("epk").getAsDouble(),
                    o.get("price_64").getAsInt(),
                    o.get("price_128").getAsInt()));
        }
    }

    @Test
    void 基准共110条且自证零逆序() {
        assertEquals(110, rows.size(), "spike 基准条目数应为 110");
        assertEquals(0, root.get("monotonic_violations").getAsInt());
    }

    @Test
    void 默认上限128_逐条零误差() {
        List<String> mismatches = new ArrayList<>();
        for (Row r : rows) {
            int got = PricingEngine.price(r.epk(), CHEAP, RARE, 128);
            if (got != r.price128()) {
                mismatches.add(r.entity() + "/" + r.item() + " epk=" + r.epk()
                        + " 基准=" + r.price128() + " Java=" + got);
            }
        }
        assertTrue(mismatches.isEmpty(), "price_max=128 分歧条目：\n" + String.join("\n", mismatches));
    }

    @Test
    void 改上限64_逐条与基准price64零误差() {
        List<String> mismatches = new ArrayList<>();
        for (Row r : rows) {
            int got = PricingEngine.price(r.epk(), CHEAP, RARE, 64);
            if (got != r.price64()) {
                mismatches.add(r.entity() + "/" + r.item() + " epk=" + r.epk()
                        + " 基准=" + r.price64() + " Java=" + got);
            }
        }
        assertTrue(mismatches.isEmpty(), "price_max=64 分歧条目：\n" + String.join("\n", mismatches));
    }

    @Test
    void 关键锚点价格() {
        // 凋灵骷髅头颅 94、铜锭 62、末影珍珠 30、腐肉 16、女巫红石 1
        assertEquals(117, price("zombie", "iron_ingot"));
        assertEquals(94, price("wither_skeleton", "wither_skeleton_skull"));
        assertEquals(62, price("drowned", "copper_ingot"));
        assertEquals(30, price("enderman", "ender_pearl"));
        assertEquals(16, price("zombie", "rotten_flesh"));
        assertEquals(1, price("witch", "redstone"));
    }

    @Test
    void 同一生物内_epk越高越便宜_全局单调() {
        Map<String, List<Row>> byEntity = new LinkedHashMap<>();
        for (Row r : rows) {
            byEntity.computeIfAbsent(r.entity(), k -> new ArrayList<>()).add(r);
        }
        for (Map.Entry<String, List<Row>> e : byEntity.entrySet()) {
            List<Row> list = e.getValue();
            list.sort((a, b) -> Double.compare(b.epk(), a.epk())); // epk 从高到低
            Integer prev = null;
            for (Row r : list) {
                int p = PricingEngine.price(r.epk(), CHEAP, RARE, 128);
                if (prev != null) {
                    assertTrue(p >= prev,
                            "违反单调（epk 降低价格不应下降）：" + e.getKey()
                                    + " " + r.item() + " epk=" + r.epk()
                                    + " price=" + p + " 上一价=" + prev);
                }
                prev = p;
            }
        }
    }

    @Test
    void 边界_零或负epk撞上限_高epk撞下限() {
        for (Row r : rows) {
            if (r.epk() <= 0.0) {
                assertEquals(128, PricingEngine.price(r.epk(), CHEAP, RARE, 128),
                        r.entity() + "/" + r.item());
            }
            if (r.epk() >= CHEAP) {
                assertEquals(1, PricingEngine.price(r.epk(), CHEAP, RARE, 128),
                        r.entity() + "/" + r.item());
            }
        }
        // 纯函数边界（基准里未必有这两个 epk，直接钉死）
        assertEquals(128, PricingEngine.price(0.0, CHEAP, RARE, 128));
        assertEquals(1, PricingEngine.price(11.0, CHEAP, RARE, 128));
    }

    @Test
    void 改price_max后曲线仍单调() {
        // 用 64 上限重算每个生物内部单调性
        Map<String, List<Row>> byEntity = new LinkedHashMap<>();
        for (Row r : rows) {
            byEntity.computeIfAbsent(r.entity(), k -> new ArrayList<>()).add(r);
        }
        for (Map.Entry<String, List<Row>> e : byEntity.entrySet()) {
            List<Row> list = e.getValue();
            list.sort((a, b) -> Double.compare(b.epk(), a.epk()));
            Integer prev = null;
            for (Row r : list) {
                int p = PricingEngine.price(r.epk(), CHEAP, RARE, 64);
                if (prev != null) {
                    assertFalse(p < prev, "price_max=64 仍须单调：" + e.getKey());
                }
                prev = p;
            }
        }
    }

    private static int price(String entity, String item) {
        for (Row r : rows) {
            if (r.entity().equals(entity) && r.item().equals(item)) {
                return PricingEngine.price(r.epk(), CHEAP, RARE, 128);
            }
        }
        throw new AssertionError("基准中缺少 " + entity + "/" + item);
    }
}
