package top.windyvalley.peaceandlove.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * 配置管理器 —— 持有当前配置，负责热重载与白名单变更。
 *
 * <p>这是配置的唯一入口（{@link PalConfig} 是不可变的，
 * 本类负责在重载时整体替换实例）。门控与定价读取配置时必须
 * 走 {@link #get()}，不得缓存，否则热重载无法生效。
 *
 * <p>热重载的安全保证（T-CFG-003 验收标准）：
 * <ul>
 *   <li><b>失败保留旧配置</b> —— 先在新对象上完整 load，成功后才替换引用，
 *       不进入半初始化状态。{@link PalConfig} 不可变保证了这一点。</li>
 *   <li><b>监听器通知</b> —— 重载成功后通知已注册的监听器（定价表重建、
 *       实体门控刷新），让它们基于新配置重新初始化。</li>
 * </ul>
 */
public final class ConfigManager {

    private static final Logger LOGGER = LoggerFactory.getLogger("Peace And Love/Config");

    private final ConfigLoader loader;
    private final List<Consumer<PalConfig>> reloadListeners = new ArrayList<>();

    /** 当前生效的配置。volatile 保证多线程（服务端 tick / 命令线程）可见。 */
    private volatile PalConfig current;

    /** 已提示过的无效白名单 id（T-SCOPE-003 去重，不刷屏）。 */
    private final java.util.Set<String> ineffectiveNotified =
            java.util.concurrent.ConcurrentHashMap.newKeySet();

    public ConfigManager(Path configDir) {
        this.loader = new ConfigLoader(configDir);
        this.current = loader.load();
        // 初次加载也提示无效白名单（T-SCOPE-003）
        logIneffectiveWhitelist(this.current);
    }

    /** 当前生效的配置。门控/定价必须从这里读，不得缓存。 */
    public PalConfig get() {
        return current;
    }

    /** 配置文件路径。 */
    public Path path() {
        return loader.path();
    }

    /**
     * 注册热重载监听器。
     *
     * <p>重载成功后按注册顺序回调，传入新配置。
     * 典型用途：定价表重建、已加载实体的门控刷新。
     */
    public void addReloadListener(Consumer<PalConfig> listener) {
        reloadListeners.add(listener);
    }

    /**
     * 热重载。
     *
     * @return 重载结果（成功与否 + 变更摘要 + 错误信息）
     */
    public ReloadResult reload() {
        PalConfig fresh;
        try {
            fresh = loader.load();
        } catch (RuntimeException e) {
            // loader 内部已尽力容错，到这里说明出现未预期错误
            LOGGER.error("配置重载失败，保留旧配置: {}", e.getMessage());
            return ReloadResult.failure("配置重载失败：" + e.getMessage());
        }

        PalConfig old = this.current;
        this.current = fresh;

        // 白名单有效性提示（T-SCOPE-003）：未适配条目打 INFO（非 WARN，
        // 这不是错误），文案说明「配置不生效，行为与原版一致」。reload 时
        // 用 Set 去重，同一 id 只提示一次，不刷屏。
        logIneffectiveWhitelist(fresh);

        ReloadResult result = ReloadResult.success(summarize(old, fresh));

        // 通知监听器（定价重建、实体刷新）。监听器异常不应让重载失败。
        for (Consumer<PalConfig> listener : reloadListeners) {
            try {
                listener.accept(fresh);
            } catch (RuntimeException e) {
                LOGGER.error("重载监听器执行失败: {}", e.getMessage());
            }
        }
        return result;
    }

    /**
     * 修改白名单并持久化。
     *
     * @param entityId 生物注册名（支持带/不带 minecraft: 前缀）
     * @param add      true=加入白名单，false=移出
     * @return 变更结果
     */
    public WhitelistChange changeWhitelist(String entityId, boolean add) {
        String id = normalize(entityId);
        List<String> current = new ArrayList<>(this.current.hostile_whitelist());

        boolean ineffective = NeutralizationScope.isIneffectiveWhitelistEntry(id);

        if (add) {
            if (current.contains(id)) {
                return WhitelistChange.noop(id + " 已在白名单中");
            }
            current.add(id);
        } else {
            if (!current.remove(id)) {
                return WhitelistChange.noop(id + " 不在白名单中");
            }
        }

        // 整体替换配置实例（不可变），保存，通知
        PalConfig updated = this.current.withWhitelist(List.copyOf(current));
        this.current = updated;
        loader.save(updated);

        for (Consumer<PalConfig> listener : reloadListeners) {
            try {
                listener.accept(updated);
            } catch (RuntimeException e) {
                LOGGER.error("白名单变更监听器执行失败: {}", e.getMessage());
            }
        }

        String action = add ? "加入" : "移出";
        String note = ineffective
                ? "（注意：" + id + " 未适配，此项配置无效，该生物行为不受影响）"
                : "";
        return WhitelistChange.done("已将 " + id + " " + action + "白名单" + note, ineffective);
    }

    /** 补全 minecraft: 前缀。 */
    private static String normalize(String id) {
        return id.contains(":") ? id : "minecraft:" + id;
    }

    /**
     * 白名单有效性提示（T-SCOPE-003）。
     *
     * <p>未适配条目打 <b>INFO 而非 WARN</b> —— 这不是错误，只是该配置
     * 对未适配生物不生效。同一 id 在两次 reload 间只提示一次，不刷屏。
     */
    private void logIneffectiveWhitelist(PalConfig cfg) {
        for (String id : cfg.hostile_whitelist()) {
            if (NeutralizationScope.isIneffectiveWhitelistEntry(id)
                    && ineffectiveNotified.add(id)) {
                LOGGER.info("白名单条目 [{}] 对应的生物 v1.0 未适配，该配置不生效，其行为与原版一致。", id);
            }
        }
        // 已不在白名单中的 id 从去重集合移除，下次再加入时可重新提示
        ineffectiveNotified.retainAll(cfg.hostile_whitelist());
    }

    /** 生成变更摘要（供命令反馈）。 */
    private static String summarize(PalConfig old, PalConfig fresh) {
        List<String> changes = new ArrayList<>();
        if (!old.hostile_whitelist().equals(fresh.hostile_whitelist())) {
            List<String> added = new ArrayList<>(fresh.hostile_whitelist());
            added.removeAll(old.hostile_whitelist());
            List<String> removed = new ArrayList<>(old.hostile_whitelist());
            removed.removeAll(fresh.hostile_whitelist());
            if (!added.isEmpty()) {
                changes.add("白名单新增 " + added);
            }
            if (!removed.isEmpty()) {
                changes.add("白名单移除 " + removed);
            }
        }
        if (old.trading_enabled() != fresh.trading_enabled()) {
            changes.add("trading_enabled: " + old.trading_enabled() + " -> " + fresh.trading_enabled());
        }
        if (old.boss_trading_enabled() != fresh.boss_trading_enabled()) {
            changes.add("boss_trading_enabled: " + old.boss_trading_enabled() + " -> " + fresh.boss_trading_enabled());
        }
        if (old.price_max() != fresh.price_max()) {
            changes.add("price_max: " + old.price_max() + " -> " + fresh.price_max());
        }
        return changes.isEmpty() ? "无变更" : String.join("；", changes);
    }

    /** 重载结果。 */
    public record ReloadResult(boolean success, String message) {
        static ReloadResult success(String summary) {
            return new ReloadResult(true, "配置已重载：" + summary);
        }

        static ReloadResult failure(String error) {
            return new ReloadResult(false, error);
        }
    }

    /** 白名单变更结果。 */
    public record WhitelistChange(boolean changed, boolean ineffective, String message) {
        static WhitelistChange done(String message, boolean ineffective) {
            return new WhitelistChange(true, ineffective, message);
        }

        static WhitelistChange noop(String message) {
            return new WhitelistChange(false, false, message);
        }
    }
}
