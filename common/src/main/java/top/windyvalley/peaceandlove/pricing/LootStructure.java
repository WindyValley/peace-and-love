package top.windyvalley.peaceandlove.pricing;

import net.minecraft.world.item.Item;
import net.minecraft.world.level.storage.loot.LootPool;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.entries.LootItem;
import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;
import net.minecraft.world.level.storage.loot.entries.LootPoolSingletonContainer;
import net.minecraft.world.level.storage.loot.functions.LootItemFunction;
import net.minecraft.world.level.storage.loot.functions.SetItemCountFunction;
import net.minecraft.world.level.storage.loot.predicates.CompositeLootItemCondition;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.level.storage.loot.providers.number.NumberProvider;
import top.windyvalley.peaceandlove.mixin.LootCompositeConditionAccessor;
import top.windyvalley.peaceandlove.mixin.LootEnchantedBonusAccessor;
import top.windyvalley.peaceandlove.mixin.LootEntryAccessor;
import top.windyvalley.peaceandlove.mixin.LootItemEntryAccessor;
import top.windyvalley.peaceandlove.mixin.LootPoolAccessor;
import top.windyvalley.peaceandlove.mixin.LootSingletonAccessor;
import top.windyvalley.peaceandlove.mixin.LootTableAccessor;
import top.windyvalley.peaceandlove.mixin.SetItemCountAccessor;

import java.util.List;

/**
 * 战利品表结构读取门面 —— 普通代码接触表结构的<b>唯一</b>入口。
 *
 * <p>存在原因与 {@code neutralize/MobAccess} 相同：所有 {@code @Accessor} Mixin
 * 接口都在 mixin 包内，普通代码直接引用会触发 Mixin 类加载约束。本类集中做
 * 「目标对象 → Accessor 接口」的强转，计算器/扫描器只认原版类型与本门面。
 *
 * <p>字段名全部经 check_loot_bytecode*.py 字节码核对（1.21.1 mojang mappings）。
 */
public final class LootStructure {

    private LootStructure() {
    }

    /** 一张表的全部池（1.21.1 中 LootTable 非 record，pools 为 private final）。 */
    public static List<LootPool> pools(LootTable table) {
        return ((LootTableAccessor) table).peaceandlove$pools();
    }

    public static List<LootPoolEntryContainer> entries(LootPool pool) {
        return ((LootPoolAccessor) pool).peaceandlove$entries();
    }

    public static List<LootItemCondition> poolConditions(LootPool pool) {
        return ((LootPoolAccessor) pool).peaceandlove$conditions();
    }

    public static NumberProvider rolls(LootPool pool) {
        return ((LootPoolAccessor) pool).peaceandlove$rolls();
    }

    /** 复合条件（all_of/any_of）的子条件；非复合条件返回空表。 */
    public static List<LootItemCondition> compositeTerms(LootItemCondition condition) {
        if (condition instanceof CompositeLootItemCondition composite) {
            return ((LootCompositeConditionAccessor) composite).peaceandlove$terms();
        }
        return List.of();
    }

    /** random_chance_with_enchanted_bonus 的未附魔概率（looting 0 基准）；类型不符抛异常。 */
    public static float unenchantedChance(LootItemCondition condition) {
        return ((LootEnchantedBonusAccessor) condition).peaceandlove$unenchantedChance();
    }

    public static List<LootItemCondition> entryConditions(LootPoolEntryContainer entry) {
        return ((LootEntryAccessor) entry).peaceandlove$conditions();
    }

    /** 条目的抽取权重；非单例条目（理论上实体表不出现）给默认权重 1。 */
    public static int weight(LootPoolEntryContainer entry) {
        if (entry instanceof LootPoolSingletonContainer singleton) {
            return ((LootSingletonAccessor) singleton).peaceandlove$weight();
        }
        return LootPoolSingletonContainer.DEFAULT_WEIGHT;
    }

    public static List<LootItemFunction> functions(LootPoolEntryContainer entry) {
        if (entry instanceof LootPoolSingletonContainer singleton) {
            return ((LootSingletonAccessor) singleton).peaceandlove$functions();
        }
        return List.of();
    }

    public static boolean isItemEntry(LootPoolEntryContainer entry) {
        return entry instanceof LootItem;
    }

    /** 条目的产出物品（调用前先经 {@link #isItemEntry} 判定）。 */
    public static Item itemOf(LootPoolEntryContainer entry) {
        return ((LootItemEntryAccessor) entry).peaceandlove$item().value();
    }

    /** 若是 set_count 函数，返回其数量提供者；否则返回 null。 */
    public static NumberProvider setCountValue(LootItemFunction function) {
        if (function instanceof SetItemCountFunction setCount) {
            return ((SetItemCountAccessor) setCount).peaceandlove$value();
        }
        return null;
    }
}
