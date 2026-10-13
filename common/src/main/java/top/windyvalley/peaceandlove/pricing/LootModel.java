package top.windyvalley.peaceandlove.pricing;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;

import java.util.List;

/**
 * 已从运行时战利品表对象中抽取出的<b>中性</b>结构 —— 只含数值，不含任何
 * 需要 Mixin Accessor 才能读的 MC 字段。
 *
 * <p>分层目的：{@code LootStructure}（Accessor 装配，仅织入后的真机可用）负责把
 * LootTable/LootPool 转成本记录；{@link DropExpectation}（纯函数，无 Mixin 依赖）
 * 负责算 epk，可纯 JUnit 覆盖。非 item 条目（empty/ref/tag）在装配阶段就被剔除，
 * 但其权重已计入 {@link EvaluatedPool#totalWeight()}。
 */
public final class LootModel {

    private LootModel() {
    }

    /** 一个 item 条目的抽取参数（条件已折算成概率与「是否保守估计」标记）。 */
    public record EvaluatedEntry(Item item, ResourceLocation itemId, int weight,
                                 double conditionProb, boolean approximated,
                                 double countExpected, int countMax) {
    }

    /** 一个池：rolls 期望、池条件概率、总权重（含 empty/ref/tag）、item 条目。 */
    public record EvaluatedPool(double rolls, double conditionProb, boolean approximated,
                                int totalWeight, List<EvaluatedEntry> entries) {
    }

    /** 一条掉落的期望产出结果（尚未定价）。 */
    public record Drop(Item item, ResourceLocation itemId, double epk,
                       int countMax, boolean approximated) {
    }
}
