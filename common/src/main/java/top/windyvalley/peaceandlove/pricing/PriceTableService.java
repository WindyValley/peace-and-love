package top.windyvalley.peaceandlove.pricing;

import dev.architectury.event.events.common.LifecycleEvent;
import net.minecraft.server.MinecraftServer;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.config.ConfigManager;
import top.windyvalley.peaceandlove.config.PalConfig;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;

import java.util.List;

/**
 * 定价表运行时接线（T-PRICE-003）：服务端启动后首建、{@code /pal reload} 后按需重建。
 *
 * <p>时机：
 * <ul>
 *   <li><b>首建</b>在 {@code SERVER_STARTED} —— 此刻数据包（含可能被覆盖的战利品表）
 *       已全部加载，{@code server.reloadableRegistries()} 是唯一权威来源（同
 *       JsonRpcService#pricingScan 的真机结论）。</li>
 *   <li><b>重建</b>订阅 {@link ConfigManager} 的重载监听；仅当定价相关字段
 *       （锚点/上限/手工修正）变化时才重建 —— 白名单增删、交易开关同样会触发该监听，
 *       但它们不影响价格，用签名守卫跳过，避免无谓扫描和刷屏日志。</li>
 * </ul>
 *
 * <p>两个回调都在服务端主线程（生命周期事件 / 命令执行），构建完成后整体替换
 * {@code volatile} 引用，运行期只读 {@link PriceTable}，与交易请求无竞态。
 * 服务关闭时清空，避免跨存档持有旧注册表对象。
 *
 * <p><b>⚠️ 已写未验</b>：生命周期触发、真实战利品表扫描与构表数字依赖运行时，
 * 纯 JUnit 覆盖不到，待随交易链接入后真机验证（可先用 verify RPC 的 pricing.scan 对照）。
 */
public final class PriceTableService {

    private final ConfigManager config;
    private final LootTableScanner scanner = new LootTableScanner();

    private volatile MinecraftServer server;
    private volatile PriceTable table = PriceTable.EMPTY;
    /** 上次构表所用定价输入签名；用于判断 reload 是否真的影响价格。 */
    private volatile String lastSignature = "";

    public PriceTableService(ConfigManager config) {
        this.config = config;
    }

    /** 注册生命周期与配置重载监听，由 {@code PeaceAndLove.init()} 调用。 */
    public void register() {
        LifecycleEvent.SERVER_STARTED.register(this::onServerStarted);
        LifecycleEvent.SERVER_STOPPED.register(this::onServerStopped);
        config.addReloadListener(this::onConfigReloaded);
        PeaceAndLove.LOGGER.info("定价表服务已接线（SERVER_STARTED 构表；定价配置变更时重建）");
    }

    /** 当前生效的不可变定价表；启动未完成时为空表（查询返回空列表，绝不 null）。 */
    public PriceTable table() {
        return table;
    }

    private void onServerStarted(MinecraftServer server) {
        this.server = server;
        rebuild(/*force*/ true);
    }

    private void onServerStopped(MinecraftServer server) {
        this.server = null;
        this.table = PriceTable.EMPTY;
        this.lastSignature = "";
    }

    /** 配置重载/白名单变更回调：只有定价输入变了才需要重建。 */
    private void onConfigReloaded(PalConfig fresh) {
        String sig = signature(fresh);
        if (sig.equals(lastSignature)) {
            return; // 白名单/交易开关等不影响价格的变更：跳过
        }
        rebuild(/*force*/ false);
    }

    /**
     * 扫描已适配生物的战利品表并构表。
     *
     * @param force true=无条件重建（首建）；false=签名未变则跳过
     */
    private synchronized void rebuild(boolean force) {
        MinecraftServer s = this.server;
        if (s == null) {
            return; // 服务端尚未就绪
        }
        PalConfig cfg = config.get();
        String sig = signature(cfg);
        if (!force && sig.equals(lastSignature)) {
            return;
        }

        var registries = s.reloadableRegistries();
        LootTableScanner.ScanResult scan = scanner.scan(
                AdaptedMobs.ALL,
                type -> registries.getLootTable(type.getDefaultLootTable()));

        PriceTable.BuildResult result = PriceTable.build(scan.entries(), cfg);
        this.table = result.table();
        this.lastSignature = sig;

        List<String> warnings = result.warnings();
        if (!warnings.isEmpty()) {
            PeaceAndLove.LOGGER.warn("定价表构建产生 {} 条告警：", warnings.size());
            for (String w : warnings) {
                PeaceAndLove.LOGGER.warn("  • {}", w);
            }
        }

        // T-PRICE-004 单调性/撞限自检：只诊断不阻断，任何意外都不能影响启服
        try {
            logSelfCheck(result.table(), cfg);
        } catch (RuntimeException e) {
            PeaceAndLove.LOGGER.warn("定价表自检执行异常（不影响服务）：{}", e.toString());
        }
    }

    /** 自检结果落日志：撞限 INFO；有逆序对则 WARN 并列前 5 个。 */
    private static void logSelfCheck(PriceTable table, PalConfig cfg) {
        PriceTable.SelfCheck chk = PriceTable.selfCheck(table, cfg);
        PeaceAndLove.LOGGER.info(
                "PAL 定价自检：共 {} 条报价，撞下限(=1) {} 条、撞上限(={}) {} 条",
                chk.totalOffers(), chk.lowerClamped(), cfg.price_max(), chk.upperClamped());
        List<String> inv = chk.inversions();
        if (!inv.isEmpty()) {
            PeaceAndLove.LOGGER.warn(
                    "PAL 定价自检发现 {} 对单调性逆序（同生物内 epk 更小却更便宜，"
                            + "通常是 price_overrides 填反或锚点过激），前 {} 个：",
                    inv.size(), Math.min(5, inv.size()));
            inv.stream().limit(5).forEach(s -> PeaceAndLove.LOGGER.warn("  • {}", s));
        }
    }

    /** 定价相关输入的签名（不含白名单/仇恨/交易开关等与价格无关的字段）。 */
    private static String signature(PalConfig c) {
        return c.epk_cheap() + "|" + c.epk_rare() + "|" + c.price_max() + "|" + c.price_overrides();
    }
}
