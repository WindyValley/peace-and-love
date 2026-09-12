package top.windyvalley.peaceandlove.fabric;

import net.fabricmc.api.ModInitializer;
import top.windyvalley.peaceandlove.ProbeCommon;

public final class ProbeFabric implements ModInitializer {
    @Override
    public void onInitialize() {
        ProbeCommon.runProbe("Fabric");
    }
}
