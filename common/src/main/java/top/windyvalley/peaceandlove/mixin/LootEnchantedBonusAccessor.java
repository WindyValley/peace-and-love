package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceWithEnchantedBonusCondition;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * 「随机概率 + 抢夺加成」条件的未附魔概率访问器。
 *
 * <p>基准 epk 以 <b>looting 0（未附魔）</b> 计算，故取 {@code unenchantedChance}；
 * {@code enchantedChance}（LevelBasedValue）是抢夺加成，不计入基准。
 *
 * <p>字节码实测：字段 {@code private final float unenchantedChance}。
 */
@Mixin(LootItemRandomChanceWithEnchantedBonusCondition.class)
public interface LootEnchantedBonusAccessor {

    @Accessor("unenchantedChance")
    float peaceandlove$unenchantedChance();
}
