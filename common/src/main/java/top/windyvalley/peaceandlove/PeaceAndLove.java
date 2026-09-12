package top.windyvalley.peaceandlove;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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

    private PeaceAndLove() {
    }

    /**
     * 公共初始化入口，由各平台的入口类调用。
     */
    public static void init() {
        LOGGER.info("Peace And Love 正在初始化");

        // TODO(T-CFG-001)   加载配置文件
        // TODO(T-SCOPE-001) 构建已适配生物清单
        // TODO(T-SCOPE-002) 初始化双重门控判定器
        // TODO(T-NEUT-001)  注册生物中立化处理
        // TODO(T-TRADE-001) 注册交易系统
        // TODO(T-CFG-003)   注册管理命令

        LOGGER.info("Peace And Love 初始化完成");
    }
}
