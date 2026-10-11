package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.level.storage.loot.entries.LootPoolSingletonContainer;
import net.minecraft.world.level.storage.loot.functions.LootItemFunction;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.List;

/**
 * {@link LootPoolSingletonContainer} 访问器：权重与函数列表。
 *
 * <p>字节码实测：{@code weight}（int）与 {@code functions} 均为 protected final。
 * {@code EmptyLootItem} / {@code NestedLootTable} / {@code TagEntry} / {@code LootItem}
 * 都继承本类 —— 权重求和覆盖同一 pool 内全部条目（含 empty/ref/tag），
 * 这与原版「加权抽取」语义一致（guardian 池 cod:2/crystals:2/empty:1 总权重 5）。
 */
@Mixin(LootPoolSingletonContainer.class)
public interface LootSingletonAccessor {

    @Accessor("weight")
    int peaceandlove$weight();

    @Accessor("functions")
    List<LootItemFunction> peaceandlove$functions();
}
