package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.List;

/**
 * {@link LootPoolEntryContainer} 条件访问器。
 *
 * <p>字节码实测：{@code conditions} 是 {@code protected final}，本模组不在
 * {@code net.minecraft...entries} 包内也非其子类，必须经 Accessor。
 */
@Mixin(LootPoolEntryContainer.class)
public interface LootEntryAccessor {

    @Accessor("conditions")
    List<LootItemCondition> peaceandlove$conditions();
}
