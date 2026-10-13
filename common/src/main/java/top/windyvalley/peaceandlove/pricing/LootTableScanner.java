package top.windyvalley.peaceandlove.pricing;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.storage.loot.LootPool;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;
import net.minecraft.world.level.storage.loot.functions.LootItemFunction;
import net.minecraft.world.level.storage.loot.providers.number.NumberProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import top.windyvalley.peaceandlove.pricing.LootModel.Drop;
import top.windyvalley.peaceandlove.pricing.LootModel.EvaluatedEntry;
import top.windyvalley.peaceandlove.pricing.LootModel.EvaluatedPool;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * 扫描原版实体战利品表，静态计算每个掉落物的「每击杀期望产出」epk —— T-PRICE-001。
 *
 * <p>两阶段分层：
 * <ol>
 *   <li><b>装配</b>（{@link #assemble}）：经 {@link LootStructure}（Mixin Accessor，
 *       仅织入后的真机/服务端可用）把 LootTable 读成中性 {@link EvaluatedPool}，
 *       非 item 条目剔除但权重计入 totalWeight；</li>
 *   <li><b>计算</b>（{@link DropExpectation}）：纯函数算 epk，可纯 JUnit 覆盖。</li>
 * </ol>
 *
 * <p>基准：玩家击杀（killed_by_player 概率记 1）、looting 0（bonusRolls 与
 * enchanted_count_increase 等抢夺加成一律不计入）。
 *
 * <p>同一物品在不同互斥分支/池出现时保留为多条（如史莱姆青蛙/非青蛙两分支各一条
 * slime_ball），与 spike 黄金基线 final_pricing_128.json 一致，合并不在本层做。
 */
public final class LootTableScanner {

    private static final Logger LOGGER = LoggerFactory.getLogger("pal-loot-scan");

    /** 按实体类型取已加载的战利品表（数据包重载后的运行时实例）。 */
    @FunctionalInterface
    public interface TableResolver {
        LootTable resolve(EntityType<?> type);
    }

    /** 一条「生物 × 掉落物」的扫描结果（尚未定价）。 */
    public record DropEntry(EntityType<?> type, ResourceLocation entityId,
                            Item item, ResourceLocation itemId,
                            double epk, int countMax, boolean approximated) {
    }

    /** 一次扫描的全部产出与诊断。 */
    public record ScanResult(List<DropEntry> entries, List<String> warnings, long elapsedMillis) {
    }

    public ScanResult scan(Collection<EntityType<?>> types, TableResolver resolver) {
        long start = System.nanoTime();
        List<DropEntry> entries = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        for (EntityType<?> type : types) {
            ResourceLocation entityId = BuiltInRegistries.ENTITY_TYPE.getKey(type);
            try {
                LootTable table = resolver.resolve(type);
                if (table == null || table == LootTable.EMPTY) {
                    // 无死亡掉落表（巨人/幻术师/蠹虫/恼鬼/凋灵[下界之星走代码]/末影螨等）。
                    continue;
                }
                List<EvaluatedPool> pools = assemble(table, entityId, warnings);
                for (Drop d : DropExpectation.compute(pools)) {
                    entries.add(new DropEntry(type, entityId, d.item(), d.itemId(),
                            d.epk(), d.countMax(), d.approximated()));
                }
            } catch (RuntimeException ex) {
                // 单表解析失败不得崩服：WARN 后跳过该生物（验收标准）。
                String msg = "战利品表扫描失败，跳过 " + entityId + ": " + ex;
                warnings.add(msg);
                LOGGER.warn(msg, ex);
            }
        }

        long elapsed = (System.nanoTime() - start) / 1_000_000;
        LOGGER.info("PAL 战利品表扫描完成：{} 生物 → {} 条可定价掉落，耗时 {} ms，{} 条告警",
                types.size(), entries.size(), elapsed, warnings.size());
        return new ScanResult(List.copyOf(entries), List.copyOf(warnings), elapsed);
    }

    /** 装配阶段：运行时 LootTable → 中性 EvaluatedPool（唯一触碰 Accessor 的地方）。 */
    private List<EvaluatedPool> assemble(LootTable table, ResourceLocation entityId,
                                         List<String> warnings) {
        List<EvaluatedPool> pools = new ArrayList<>();
        for (LootPool pool : LootStructure.pools(table)) {
            double rolls = NumberExpectations.expected(LootStructure.rolls(pool));
            ConditionProbability.Result poolCond =
                    ConditionProbability.evaluate(LootStructure.poolConditions(pool));

            List<LootPoolEntryContainer> raw = LootStructure.entries(pool);
            int totalWeight = 0;
            for (LootPoolEntryContainer e : raw) {
                totalWeight += Math.max(0, LootStructure.weight(e));
            }

            List<EvaluatedEntry> entries = new ArrayList<>();
            for (LootPoolEntryContainer e : raw) {
                if (!LootStructure.isItemEntry(e)) {
                    continue; // empty / loot_table 引用 / tag 等不直接产出可定价物品
                }
                ConditionProbability.Result entryCond =
                        ConditionProbability.evaluate(LootStructure.entryConditions(e));
                List<LootItemFunction> functions = LootStructure.functions(e);
                Item item = LootStructure.itemOf(e);
                entries.add(new EvaluatedEntry(
                        item,
                        BuiltInRegistries.ITEM.getKey(item),
                        LootStructure.weight(e),
                        entryCond.probability(),
                        entryCond.approximated(),
                        countExpectation(functions),
                        countMax(functions)));
            }

            if (poolCond.approximated()
                    || entries.stream().anyMatch(EvaluatedEntry::approximated)) {
                for (EvaluatedEntry e : entries) {
                    warnings.add("含不可静态求值条件，概率按 0.3 保守估计: "
                            + entityId + "/" + e.itemId());
                }
            }
            pools.add(new EvaluatedPool(rolls, poolCond.probability(), poolCond.approximated(),
                    totalWeight, List.copyOf(entries)));
        }
        return pools;
    }

    /**
     * 数量期望：取（最后一个）set_count 覆盖值，无则 1。enchanted_count_increase
     * 是抢夺加成，looting 0 贡献 0，不识别。limit_count 在适配实体表零出现，不支持。
     */
    private double countExpectation(List<LootItemFunction> functions) {
        double base = 1.0;
        for (LootItemFunction fn : functions) {
            NumberProvider value = LootStructure.setCountValue(fn);
            if (value != null) {
                base = NumberExpectations.expectedCountClamped(value);
            }
        }
        return Math.max(0.0, base);
    }

    /** 数量上界（looting 0）：set_count 上界，默认 1。 */
    private int countMax(List<LootItemFunction> functions) {
        int max = 1;
        for (LootItemFunction fn : functions) {
            NumberProvider value = LootStructure.setCountValue(fn);
            if (value != null) {
                max = Math.max(max, NumberExpectations.maxCount(value));
            }
        }
        return max;
    }
}
