package top.windyvalley.peaceandlove.mixin;

import net.minecraft.core.Holder;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.storage.loot.entries.LootItem;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * {@link LootItem} 的物品访问器。
 *
 * <p>字节码实测：字段为 {@code private final Holder<Item> item}，
 * 取 {@code .value()} 得注册的 {@link Item}。
 */
@Mixin(LootItem.class)
public interface LootItemEntryAccessor {

    @Accessor("item")
    Holder<Item> peaceandlove$item();
}
