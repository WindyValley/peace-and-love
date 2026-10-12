package top.windyvalley.peaceandlove.pricing;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.Item;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import top.windyvalley.peaceandlove.config.PalConfig;
import top.windyvalley.peaceandlove.pricing.LootTableScanner.DropEntry;
import top.windyvalley.peaceandlove.trade.TradeSpec;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 不可变定价表 —— 启动/reload 时一次性构建，运行期只读，T-PRICE-003。
 *
 * <p>权威结构对齐设计 §5.1：{@code EntityType → List<TradeSpec>}。<b>同一生物的同一
 * 物品可能有多条报价</b>，这是有意保留而非缺陷：原版战利品表里互斥分支可掉落同一物品
 * 但掉落量不同（例如史莱姆的黏液球，青蛙击杀分支掉 2 个、普通分支掉 1 个，epk 与价格
 * 都不同，见 spike 黄金基线 final_pricing_128.json 中 slime/slime_ball 的两条）。
 * 扫描层注释已声明「合并不在本层做」，这里若按 {@code (生物,物品)} 压成单值会丢失掉落量
 * 维度，故保留为多条，交给交易 GUI 呈现为多个报价。
 *
 * <p>查询均为 O(1)：{@link #offersFor(EntityType)} 走 {@code byEntity}，
 * {@link #offersFor(EntityType, Item)} 走扁平索引 {@code byEntityItem}。
 *
 * <p>不可变性：构建期使用可变 Map 收集，发布前一律 {@code Map.copyOf/List.copyOf}；
 * 发布后没有任何途径修改内部结构（无 setter、防御性拷贝），因此多线程读安全，
 * 与 ConfigManager「整体替换 volatile 引用」的热重载模型配合无竞态。
 */
public final class PriceTable {

    private static final Logger LOGGER = LoggerFactory.getLogger("Peace And Love/PriceTable");

    /** MerchantOffer 双输入槽 64+64 的物理上限，override 也不得超过。 */
    static final int HARD_PRICE_LIMIT = 128;

    /** 启动尚未完成 / 构建失败时的空表，保证查询永不返回 null。 */
    public static final PriceTable EMPTY = new PriceTable(Map.of(), Map.of());

    private final Map<EntityType<?>, List<TradeSpec>> byEntity;
    private final Map<EntityItemKey, List<TradeSpec>> byEntityItem;
    /** 表内容指纹：生物→(物品,数量,价格) 规范化后的稳定哈希。改价/reload 后变化，供持久化报价失效判定。 */
    private final long fingerprint;

    private PriceTable(Map<EntityType<?>, List<TradeSpec>> byEntity,
                       Map<EntityItemKey, List<TradeSpec>> byEntityItem) {
        this.byEntity = byEntity;
        this.byEntityItem = byEntityItem;
        this.fingerprint = computeFingerprint(byEntity);
    }

    /** (生物, 物品) 复合键 —— 仅作扁平索引，值为该组合下的全部报价（可能多条）。 */
    private record EntityItemKey(EntityType<?> type, Item item) {
    }

    /**
     * 把扫描出的掉落期望按当前配置定价，构建不可变定价表（纯逻辑，可单测）。
     *
     * <p>每条 {@link DropEntry}：价格优先取 {@code price_overrides} 手工修正，
     * 否则走 {@link ConfigurablePriceCurve}；产出量取 looting 0 上界 {@code countMax}。
     *
     * @param drops  扫描结果（T-PRICE-001）
     * @param config 当前配置（锚点/上限/手工修正）
     */
    public static BuildResult build(List<DropEntry> drops, PalConfig config) {
        long start = System.nanoTime();
        List<String> warnings = new ArrayList<>();

        Map<EntityType<?>, List<TradeSpec>> byEntity = new LinkedHashMap<>();
        Map<EntityItemKey, List<TradeSpec>> byEntityItem = new LinkedHashMap<>();
        // 本次构建实际命中的 override key，用于最后反查「配了但没对应掉落」的无效修正
        java.util.Set<String> usedOverrides = new java.util.HashSet<>();

        for (DropEntry d : drops) {
            int price = resolvePrice(d, config, warnings, usedOverrides);
            TradeSpec spec;
            try {
                spec = new TradeSpec(d.item(), d.countMax(), price, d.epk());
            } catch (RuntimeException e) {
                // 单条非法（理论上价格已 clamp、countMax>=1，不会到这）：跳过而非崩构建
                warnings.add("跳过非法报价 " + d.entityId() + "/" + d.itemId() + ": " + e);
                continue;
            }
            byEntity.computeIfAbsent(d.type(), k -> new ArrayList<>()).add(spec);
            byEntityItem.computeIfAbsent(new EntityItemKey(d.type(), d.item()), k -> new ArrayList<>()).add(spec);
        }

        // 提示管理员：配了 override 却没有对应掉落（多半是 id 拼错或该生物不掉此物）
        for (String key : config.price_overrides().keySet()) {
            if (!usedOverrides.contains(key)) {
                warnings.add("price_overrides[" + key + "] 未匹配到任何可定价掉落，已忽略（请检查 实体ID/物品ID）");
            }
        }

        // 冻结
        Map<EntityType<?>, List<TradeSpec>> frozenEntity = new LinkedHashMap<>();
        byEntity.forEach((t, list) -> frozenEntity.put(t, List.copyOf(list)));
        Map<EntityItemKey, List<TradeSpec>> frozenPair = new LinkedHashMap<>();
        byEntityItem.forEach((k, list) -> frozenPair.put(k, List.copyOf(list)));

        long elapsed = (System.nanoTime() - start) / 1_000_000;
        int offerCount = frozenPair.values().stream().mapToInt(List::size).sum();
        LOGGER.info("PAL 定价表构建完成：{} 生物、{} 条报价，耗时 {} ms，{} 条告警",
                frozenEntity.size(), offerCount, elapsed, warnings.size());

        PriceTable table = new PriceTable(Map.copyOf(frozenEntity), Map.copyOf(frozenPair));
        return new BuildResult(table, List.copyOf(warnings), elapsed, offerCount);
    }

    /** 定价：override 优先（clamp 到 [1, price_max]），否则走配置曲线。 */
    private static int resolvePrice(DropEntry d, PalConfig config,
                                    List<String> warnings, Set<String> usedOverrides) {
        String key = d.entityId().toString() + "/" + d.itemId().toString();
        Integer override = config.price_overrides().get(key);
        if (override != null) {
            usedOverrides.add(key);
            int max = Math.min(config.price_max(), HARD_PRICE_LIMIT);
            if (override < 1 || override > max) {
                int clamped = Math.max(1, Math.min(max, override));
                warnings.add("price_overrides[" + key + "]=" + override
                        + " 越界，clamp 为 " + clamped + "（合法区间 [1," + max + "]）");
                return clamped;
            }
            return override;
        }
        return ConfigurablePriceCurve.price(d.epk(), config);
    }

    // ── 查询（全部 O(1)，返回不可变列表）──

    /**
     * 表内容指纹。同一掉落表 + 同一配置两次构建结果相同；改价 / 改锚点 / 改掉落量后变化。
     *
     * <p>用于让随实体存档的报价（购买次数 uses）在定价变更后失效重建，而不是沿用旧报价。
     * 只纳入影响交易的字段（生物、物品、数量、价格），不含 epk（epk 变但价格没变时不必丢购买次数）。
     */
    public long fingerprint() {
        return fingerprint;
    }

    /** 规范化（EntityType 注册名排序）后的稳定哈希；只纳入影响交易的字段。 */
    private static long computeFingerprint(Map<EntityType<?>, List<TradeSpec>> byEntity) {
        List<Map.Entry<EntityType<?>, List<TradeSpec>>> entries = new java.util.ArrayList<>(byEntity.entrySet());
        entries.sort(java.util.Comparator.comparing(
                e -> BuiltInRegistries.ENTITY_TYPE.getKey(e.getKey()).toString()));
        long h = 1_469_598_539_037_040_107L; // 素数基数
        for (Map.Entry<EntityType<?>, List<TradeSpec>> e : entries) {
            h = h * 31 + BuiltInRegistries.ENTITY_TYPE.getKey(e.getKey()).toString().hashCode();
            for (TradeSpec s : e.getValue()) {
                h = h * 31 + BuiltInRegistries.ITEM.getKey(s.item()).toString().hashCode();
                h = h * 31 + s.count();
                h = h * 31 + s.price();
            }
        }
        return h;
    }

    /** 该生物的全部报价；无掉落/未适配返回空列表。 */
    public List<TradeSpec> offersFor(EntityType<?> type) {
        return byEntity.getOrDefault(type, List.of());
    }

    /** 该生物出售指定物品的全部报价（互斥分支可能多条）；无则空列表。 */
    public List<TradeSpec> offersFor(EntityType<?> type, Item item) {
        return byEntityItem.getOrDefault(new EntityItemKey(type, item), List.of());
    }

    /** 表内报价总条数。 */
    public int size() {
        return byEntityItem.values().stream().mapToInt(List::size).sum();
    }

    /** 表内有报价的生物类型集合（不可变）。 */
    public Set<EntityType<?>> entities() {
        return byEntity.keySet();
    }

    /**
     * 定价单调性自检（T-PRICE-004）。
     *
     * <p>对数曲线本身保证单调：同一生物内 epk 越小（越稀有）价格应越高。逆序对只会在
     * 手工 {@code price_overrides} 填反、或锚点被改得极端时出现。本方法<b>只检查、不修改、
     * 不抛异常</b>，结果交给调用方打日志，绝不阻断启动。
     *
     * <p>逆序对定义（卡验收原文）：同一生物内，A 的 epk 比 B 小（更稀有），价格却比 B 低。
     * 同价不同 epk（撞顶/撞底的平台期）不算逆序。
     */
    public static SelfCheck selfCheck(PriceTable table, PalConfig config) {
        int max = config.price_max();
        int total = 0, lowerClamped = 0, upperClamped = 0;
        List<String> inversions = new ArrayList<>();

        for (Map.Entry<EntityType<?>, List<TradeSpec>> e : table.byEntity.entrySet()) {
            EntityType<?> type = e.getKey();
            List<TradeSpec> offers = e.getValue();
            for (TradeSpec s : offers) {
                total++;
                if (s.price() <= 1) {
                    lowerClamped++;
                }
                if (s.price() >= max) {
                    upperClamped++;
                }
            }
            for (int i = 0; i < offers.size(); i++) {
                for (int j = i + 1; j < offers.size(); j++) {
                    TradeSpec a = offers.get(i);
                    TradeSpec b = offers.get(j);
                    // a 更稀有却更便宜，或反之（同价平台期不算）
                    if ((a.epk() < b.epk() && a.price() < b.price())
                            || (a.epk() > b.epk() && a.price() > b.price())) {
                        inversions.add(describe(type, a) + "  ⇄  " + describe(type, b));
                    }
                }
            }
        }
        return new SelfCheck(total, lowerClamped, upperClamped, List.copyOf(inversions));
    }

    /** 形如 "zombie/iron_ingot(epk=0.0083,price=117)" 的定位串，供日志列出前 5 个。 */
    private static String describe(EntityType<?> type, TradeSpec s) {
        String entity = BuiltInRegistries.ENTITY_TYPE.getKey(type).getPath();
        String item = BuiltInRegistries.ITEM.getKey(s.item()).getPath();
        return String.format("%s/%s(epk=%g,price=%d)", entity, item, s.epk(), s.price());
    }

    /** 自检结果：报价总数、撞下限(=1)/撞上限(=price_max)数、逆序对描述列表。 */
    public record SelfCheck(int totalOffers, int lowerClamped, int upperClamped,
                            List<String> inversions) {
        /** 无逆序对即健康（撞限本身只是 INFO，不是错误）。 */
        public boolean healthy() {
            return inversions.isEmpty();
        }
    }

    /** 构建结果：表 + 诊断。 */
    public record BuildResult(PriceTable table, List<String> warnings,
                              long elapsedMillis, int offerCount) {
    }
}
