package top.windyvalley.peaceandlove.mixin;

import net.minecraft.world.level.storage.loot.LootPool;
import net.minecraft.world.level.storage.loot.LootTable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import java.util.List;

/**
 * {@link LootTable} 结构访问器。
 *
 * <p><b>字节码实测</b>（check_loot_bytecode.py，1.21.1 mojang mappings）：
 * 1.21.1 的 {@code LootTable} <b>不是 record</b>，没有 {@code pools()} 方法，
 * {@code pools} 是 private final 字段，必须经 Accessor 读取（设计文档 §4.3
 * 「record accessor 零 Mixin」的描述与实际字节码不符，以此为准）。
 *
 * <p>⚠️ Mixin 类加载约束：普通代码不得直接引用本接口，一律经
 * {@code pricing/LootStructure} 门面。
 */
@Mixin(LootTable.class)
public interface LootTableAccessor {

    @Accessor("pools")
    List<LootPool> peaceandlove$pools();
}
