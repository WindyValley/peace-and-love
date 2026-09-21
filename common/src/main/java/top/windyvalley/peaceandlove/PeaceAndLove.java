package top.windyvalley.peaceandlove;

import dev.architectury.event.events.common.LifecycleEvent;
import dev.architectury.platform.Platform;
import net.minecraft.server.MinecraftServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import top.windyvalley.peaceandlove.config.ConfigCommand;
import top.windyvalley.peaceandlove.config.ConfigManager;
import top.windyvalley.peaceandlove.neutralize.NeutralizationService;
import top.windyvalley.peaceandlove.verify.JsonRpcService;

/**
 * 模组公共入口。
 *
 * <p>两端（Fabric / NeoForge）的平台入口类都调用 {@link #init()}，
 * 所有业务逻辑集中在 common 模块，平台模块只做转发。
 *
 * <p>初始化顺序有讲究：配置必须最先加载，因为「已适配清单」和
 * 「白名单」共同决定哪些生物被中立化，后续所有系统都依赖这个判定结果。
 */
public final class PeaceAndLove {

    /** 模组 ID，与 gradle.properties 的 mod_id 保持一致 */
    public static final String MOD_ID = "peaceandlove";

    public static final Logger LOGGER = LoggerFactory.getLogger("Peace And Love");

    /** 配置管理器单例，门控/定价/命令共用。 */
    private static ConfigManager configManager;

    /** 中立化服务单例。 */
    private static NeutralizationService neutralizationService;

    /** JSON-RPC 验证服务（仅测试环境开启）。 */
    private static JsonRpcService jsonRpcService;

    /** 服务端实例，ServerLifecycleEvent 回调时赋值。 */
    private static MinecraftServer minecraftServer;

    private PeaceAndLove() {
    }

    /**
     * 公共初始化入口，由各平台的入口类调用。
     */
    public static void init() {
        LOGGER.info("Peace And Love 正在初始化");

        // 配置最先加载 —— 门控判定依赖它
        configManager = new ConfigManager(Platform.getConfigFolder());

        // 中立化接线（T-NEUT）：实体生成时 neutralize + Brain 系每 tick 擦除
        neutralizationService = new NeutralizationService(configManager);
        neutralizationService.register();

        // 仇恨衰减接线（T-ANGER-004）：Goal 系每 tick 脱战判定
        new top.windyvalley.peaceandlove.anger.AngerDecayService().register();

        // 服务端生命周期：启动时开启 JSON-RPC，关闭时停止。
        // 仅在显式开启调试端口的构建里生效（正式构建常量为 false，代码被编译消除）。
        if (BuildFlags.ENABLE_VERIFY_RPC) {
            LifecycleEvent.SERVER_STARTING.register(server -> {
                minecraftServer = server;
                jsonRpcService = new JsonRpcService(server);
                jsonRpcService.start();
                LOGGER.info("[JSON-RPC] 验证服务已随服务端启动");
            });
            LifecycleEvent.SERVER_STOPPED.register(server -> {
                if (jsonRpcService != null) {
                    jsonRpcService.stop();
                    jsonRpcService = null;
                }
                minecraftServer = null;
            });
        }

        // TODO(T-TRADE-001) 注册交易系统

        // 命令最后注册（依赖配置就绪）
        new ConfigCommand(configManager).register();

        LOGGER.info("Peace And Love 初始化完成");
    }

    /** 全局配置管理器。 */
    public static ConfigManager config() {
        return configManager;
    }

    /** 中立化服务（供 AngerController 接线 anger 探针）。 */
    public static NeutralizationService neutralization() {
        return neutralizationService;
    }

    /** JSON-RPC 验证服务。 */
    public static JsonRpcService jsonRpc() {
        return jsonRpcService;
    }
}
