package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.level.storage.loot.LootPool;
import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraft.world.level.storage.loot.providers.number.NumberProvider;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.List;

/**
 * {@link LootPool} 结构访问器。
 *
 * <p>字节码实测：{@code entries} / {@code conditions} / {@code rolls} 均为
 * private final（普通类无法访问）。{@code bonusRolls} 不读 —— 基准 epk 以
 * looting 0 计算，bonusRolls 是抢夺加成，不计入。
 */
@Mixin(LootPool.class)
public interface LootPoolAccessor {

    @Accessor("entries")
    List<LootPoolEntryContainer> peaceandlove$entries();

    @Accessor("conditions")
    List<LootItemCondition> peaceandlove$conditions();

    @Accessor("rolls")
    NumberProvider peaceandlove$rolls();
}
