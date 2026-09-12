package top.windyvalley.peaceandlove.fabric;

import net.fabricmc.api.ModInitializer;
import top.windyvalley.peaceandlove.PeaceAndLove;

/**
 * Fabric 平台入口。
 *
 * <p>只做转发，不含业务逻辑 —— 所有实现在 common 模块的
 * {@link PeaceAndLove#init()}。
 */
public final class PeaceAndLoveFabric implements ModInitializer {

    @Override
    public void onInitialize() {
        PeaceAndLove.init();
    }
}
