package top.windyvalley.peaceandlove.pricing;

import net.minecraft.world.level.storage.loot.predicates.AllOfCondition;
import net.minecraft.world.level.storage.loot.predicates.AnyOfCondition;
import net.minecraft.world.level.storage.loot.predicates.BonusLevelTableCondition;
import net.minecraft.world.level.storage.loot.predicates.InvertedLootItemCondition;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.level.storage.loot.predicates.LootItemKilledByPlayerCondition;
import net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceCondition;
import net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceWithEnchantedBonusCondition;

import java.util.List;

/**
 * 条件链的静态命中概率 —— 对齐 spike price_algo_v3.py 的 {@code cond_prob}。
 *
 * <p>基准：玩家击杀、looting 0。
 * <ul>
 *   <li>{@code killed_by_player}：基准即玩家击杀 → 概率 1；</li>
 *   <li>{@code random_chance}：取 chance NumberProvider 的期望；</li>
 *   <li>{@code random_chance_with_enchanted_bonus}：取<b>未附魔</b>概率；</li>
 *   <li>{@code table_bonus}：取第 0 档（无抢夺）概率；</li>
 *   <li>{@code all_of}：各子条件概率相乘；{@code any_of}：取最大；
 *       {@code inverted}：1−子条件概率（钳到 ≥0）；</li>
 *   <li><b>未知运行时条件</b>（entity_properties / damage_source_properties 等，
 *       依赖击杀现场无法静态求值）：保守乘 {@link #UNKNOWN_FACTOR}=0.3，
 *       并标记 approximated=true 供日志提示。</li>
 * </ul>
 *
 * <p>0.3 是 spike 起就固定的保守系数：既不把无法判定的条件当必然命中（高估产出、
 * 定价偏低），也不直接归零（弃售）。slime 的两池互斥掉落、slime 体型限制等都走它。
 */
public final class ConditionProbability {

    /** 无法静态求值条件的保守命中系数（与 spike 一致，勿擅改，改了定价基线就变）。 */
    public static final double UNKNOWN_FACTOR = 0.3;

    private ConditionProbability() {
    }

    /** 概率评估结果。 */
    public record Result(double probability, boolean approximated) {
        static Result exact(double p) {
            return new Result(p, false);
        }
    }

    /** 评估一串 AND 组合的条件（pool/entry 顶层即 AND 语义）。 */
    public static Result evaluate(List<LootItemCondition> conditions) {
        double prob = 1.0;
        boolean approximated = false;
        for (LootItemCondition c : conditions) {
            Result r = evaluateOne(c);
            prob *= r.probability;
            approximated |= r.approximated;
        }
        return new Result(prob, approximated);
    }

    private static Result evaluateOne(LootItemCondition c) {
        if (c instanceof LootItemKilledByPlayerCondition) {
            return Result.exact(1.0);
        }
        if (c instanceof LootItemRandomChanceCondition chance) {
            return Result.exact(NumberExpectations.expected(chance.chance()));
        }
        if (c instanceof LootItemRandomChanceWithEnchantedBonusCondition) {
            return Result.exact(LootStructure.unenchantedChance(c));
        }
        if (c instanceof BonusLevelTableCondition tableBonus) {
            List<Float> values = tableBonus.values();
            return Result.exact(values.isEmpty() ? 1.0 : values.get(0));
        }
        if (c instanceof AllOfCondition) {
            return evaluate(LootStructure.compositeTerms(c));
        }
        if (c instanceof AnyOfCondition) {
            double max = 0.0;
            boolean approximated = false;
            for (LootItemCondition term : LootStructure.compositeTerms(c)) {
                Result r = evaluateOne(term);
                max = Math.max(max, r.probability);
                approximated |= r.approximated;
            }
            return new Result(max, approximated);
        }
        if (c instanceof InvertedLootItemCondition inverted) {
            Result r = evaluateOne(inverted.term());
            return new Result(Math.max(0.0, 1.0 - r.probability), r.approximated);
        }
        // 依赖击杀现场（伤害来源、实体属性、位置、天气等），无法静态求值。
        return new Result(UNKNOWN_FACTOR, true);
    }
}
