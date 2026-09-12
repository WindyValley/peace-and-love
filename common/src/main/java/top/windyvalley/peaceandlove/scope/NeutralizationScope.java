package top.windyvalley.peaceandlove.scope;

import net.minecraft.world.entity.EntityType;
import top.windyvalley.peaceandlove.config.PalConfig;

import java.util.Set;

/**
 * 双重决策门控 —— 全项目的行为总开关。
 *
 * <p>一个生物是否被中立化、能否交易，全部经由本类判定。
 * 任何模块不得绕过它自行判断。
 *
 * <p><b>核心规则（这是设计阶段反复纠正过的点，务必读 {@code docs/adr/004}）：</b>
 * <pre>
 * 被中立化 = 在已适配列表 AND 不在白名单
 * </pre>
 *
 * <p>「已适配列表」与「白名单」是<b>两个不同语义</b>，不可混为一谈：
 * <ul>
 *   <li><b>已适配列表</b>({@link AdaptedMobs}) —— 代码能力边界，编译期常量，
 *       决定模组<b>有没有能力</b>中立化某生物。第三方 Mod 的生物天然不在其中，
 *       因此完全不受影响 —— 这是免疫机制，不是靠白名单实现的。</li>
 *   <li><b>白名单</b>({@link PalConfig#hostile_whitelist}) —— 运行时配置，
 *       决定管理员<b>要不要</b>中立化某个已适配的生物。</li>
 * </ul>
 *
 * <p>真值表：
 * <pre>
 * 已适配 | 在白名单 | 结果
 *   ✅   |   ❌    | 中立化
 *   ✅   |   ✅    | 保持原版
 *   ❌   |   ❌    | 保持原版
 *   ❌   |   ✅    | 保持原版（配置无效）
 * </pre>
 */
public final class NeutralizationScope {

    /**
     * 需要 boss_trading_enabled 额外开关的 Boss 生物。
     *
     * <p>与凋灵同等对待原则（docs/02-design.md §10）：凋灵与监守者都已适配、
     * 默认中立化，但 {@code boss_trading_enabled=false} 时不开交易。
     */
    private static final Set<EntityType<?>> BOSSES = Set.of(
            EntityType.WITHER,
            EntityType.WARDEN
    );

    private NeutralizationScope() {
    }

    /**
     * 该生物是否被中立化（核心门控）。
     *
     * <p>读配置当前值，<b>不缓存</b> —— 白名单热重载后立即生效。
     */
    public static boolean isNeutralized(EntityType<?> type, PalConfig cfg) {
        return AdaptedMobs.isAdapted(type) && !cfg.whitelistSet().contains(id(type));
    }

    /**
     * 该生物能否交易。
     *
     * <p>前提是中立化，再叠加交易开关：
     * <pre>
     * canTrade = isNeutralized AND trading_enabled AND (非Boss OR boss_trading_enabled)
     * </pre>
     */
    public static boolean canTrade(EntityType<?> type, PalConfig cfg) {
        if (!isNeutralized(type, cfg)) {
            return false;
        }
        if (!cfg.trading_enabled()) {
            return false;
        }
        if (BOSSES.contains(type) && !cfg.boss_trading_enabled()) {
            return false;
        }
        return true;
    }

    /**
     * 配置项是否「无效」—— 即白名单里列了一个根本未适配的生物。
     *
     * <p>用于启动/重载时打 INFO 日志提醒管理员（docs/02-design.md §10：
     * 「配置无效，日志给 INFO 提示」）。例如把末影龙加进白名单是无效的，
     * 因为它没适配，行为本来就完全不变。
     */
    public static boolean isIneffectiveWhitelistEntry(String entityId) {
        // 无法直接由 id 反查 EntityType（需要注册表），这里只在已知适配 id 集合里查。
        return !AdaptedMobs.adaptedIds().contains(entityId);
    }

    /** 该生物是否为 Boss（需 boss_trading_enabled 额外开关）。 */
    public static boolean isBoss(EntityType<?> type) {
        return BOSSES.contains(type);
    }

    private static String id(EntityType<?> type) {
        // EntityType 的注册名，如 "minecraft:zombie"
        return net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE
                .getKey(type).toString();
    }
}
