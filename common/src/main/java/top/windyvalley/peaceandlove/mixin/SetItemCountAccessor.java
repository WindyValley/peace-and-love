package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.level.storage.loot.functions.SetItemCountFunction;
import net.minecraft.world.level.storage.loot.providers.number.NumberProvider;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * {@link SetItemCountFunction} 数量提供者访问器。
 *
 * <p>字节码实测：字段名是 {@code value}（NumberProvider），不是泛泛的 count；
 * 另有 boolean {@code add}（false=覆盖式 set_count，true=在原数量上加）。
 * 实体掉落表中 set_count 全部是覆盖式，epk 计算取 value 的期望即可；
 * 不读 {@code add}，但保留字段事实备查。
 */
@Mixin(SetItemCountFunction.class)
public interface SetItemCountAccessor {

    @Accessor("value")
    NumberProvider peaceandlove$value();
}
