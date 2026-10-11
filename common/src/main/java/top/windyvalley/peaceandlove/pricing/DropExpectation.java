package top.windyvalley.peaceandlove.pricing;

import top.windyvalley.peaceandlove.pricing.LootModel.Drop;
import top.windyvalley.peaceandlove.pricing.LootModel.EvaluatedEntry;
import top.windyvalley.peaceandlove.pricing.LootModel.EvaluatedPool;

import java.util.ArrayList;
import java.util.List;

/**
 * epk 纯计算 —— 输入中性的 {@link EvaluatedPool}（不含任何需 Mixin 读取的 MC 对象），
 * 输出每条掉落的期望产出。无 Mixin/注册表依赖，可纯 JUnit 覆盖。
 *
 * <p>公式（对齐 spike price_algo_v3.py）：
 * <pre>
 *   epk = rolls × Π池条件 × (entryWeight / 池总权重) × Πentry条件 × E[数量]
 * </pre>
 * 池总权重含 empty/ref/tag 条目（装配阶段计入 totalWeight，条目本身不产出行）。
 * 同一物品在不同互斥分支/池出现时保留为多条（如史莱姆 slime_ball 两条），不在此合并。
 * epk &le; 0 的条目丢弃（不定天价）。
 */
public final class DropExpectation {

    private DropExpectation() {
    }

    public static List<Drop> compute(List<EvaluatedPool> pools) {
        List<Drop> drops = new ArrayList<>();
        for (EvaluatedPool pool : pools) {
            if (pool.totalWeight() <= 0) {
                continue;
            }
            double poolFactor = pool.rolls() * pool.conditionProb();
            for (EvaluatedEntry e : pool.entries()) {
                int weight = Math.max(0, e.weight());
                double epk = poolFactor
                        * ((double) weight / pool.totalWeight())
                        * e.conditionProb()
                        * e.countExpected();
                if (epk <= 0.0) {
                    continue;
                }
                drops.add(new Drop(e.item(), e.itemId(), epk, e.countMax(),
                        pool.approximated() || e.approximated()));
            }
        }
        return drops;
    }
}
