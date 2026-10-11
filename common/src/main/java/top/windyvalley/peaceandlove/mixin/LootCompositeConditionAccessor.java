package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.level.storage.loot.predicates.CompositeLootItemCondition;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.List;

/**
 * 复合条件（{@code AllOfCondition} / {@code AnyOfCondition}）子条件访问器。
 *
 * <p>字节码实测：两者都继承 {@link CompositeLootItemCondition}，子条件存于
 * {@code protected final List<LootItemCondition> terms}，无 public accessor。
 * {@code InvertedLootItemCondition} 的 term() 是 public record 风格访问器，无需本类。
 */
@Mixin(CompositeLootItemCondition.class)
public interface LootCompositeConditionAccessor {

    @Accessor("terms")
    List<LootItemCondition> peaceandlove$terms();
}
