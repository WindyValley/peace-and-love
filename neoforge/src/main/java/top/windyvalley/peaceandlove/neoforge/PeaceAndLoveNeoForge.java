package top.windyvalley.peaceandlove.neoforge;

import net.neoforged.fml.common.Mod;
import top.windyvalley.peaceandlove.PeaceAndLove;

/**
 * NeoForge 平台入口。
 *
 * <p>NeoForge 通过 {@code @Mod} 注解的构造器完成初始化，
 * modId 必须与 neoforge.mods.toml 中声明的一致。
 */
@Mod(PeaceAndLove.MOD_ID)
public final class PeaceAndLoveNeoForge {

    public PeaceAndLoveNeoForge() {
        PeaceAndLove.init();
    }
}
