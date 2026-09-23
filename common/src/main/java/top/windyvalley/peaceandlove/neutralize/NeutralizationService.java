package top.windyvalley.peaceandlove.neutralize;

import dev.architectury.event.EventResult;
import dev.architectury.event.events.common.EntityEvent;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.config.ConfigManager;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 中立化接线服务 —— 把策略挂到服务端运行时。
 *
 * <p>只有一个挂点：{@code EntityEvent.ADD}。实体加入世界时，若门控判定
 * 「中立化生效」，按策略 neutralize：
 * <ul>
 *   <li>Goal 系：一次性移除索敌 Goal 即完成；</li>
 *   <li>Brain 系：做一次初始目标清理；之后的持续拦截由 {@code BrainMixin}
 *       在记忆写入源头完成，不再需要每 tick 遍历全服实体。</li>
 * </ul>
 *
 * <p><b>门控在挂点入口判定</b>：事件里对每个实体先过
 * {@link NeutralizationScope#isNeutralized}，白名单/未适配的直接跳过。
 *
 * <p><b>⚠️ 验证方式</b>：事件的实际触发、Mixin 注入、策略对真实 Mob 的
 * 效果，均依赖服务端运行时，无法用纯 JUnit 验证。本类标注「已写未验」，
 * 待部署到测试服务端后真机验证。
 */
public final class NeutralizationService {

    private final StrategyRegistry registry;
    private final ConfigManager config;

    public NeutralizationService(ConfigManager config) {
        this.config = config;
        this.registry = new StrategyRegistry();
        // BrainBased 特例先于 GoalBased 兜底注册
        this.registry.register(new BrainBasedStrategy())
                .register(new GoalBasedStrategy());
    }

    /** 注册事件监听，由 {@code PeaceAndLove.init()} 调用。 */
    public void register() {
        EntityEvent.ADD.register(this::onEntityAdd);
        PeaceAndLove.LOGGER.info("中立化服务已接线（EntityEvent.ADD；Brain 持续拦截由 BrainMixin 负责）");
    }

    /** 实体加入世界：门控通过则 neutralize。 */
    private EventResult onEntityAdd(Entity entity, net.minecraft.world.level.Level level) {
        // 只在服务端处理；客户端实体不操作 AI
        if (level.isClientSide() || !(entity instanceof Mob mob)) {
            return EventResult.pass();
        }
        if (!NeutralizationScope.isNeutralized(mob.getType(), config.get())) {
            return EventResult.pass();
        }
        try {
            registry.strategyFor(mob.getType()).neutralize(mob);
        } catch (RuntimeException e) {
            // 单个实体失败不应拖垮流程；记日志后继续
            PeaceAndLove.LOGGER.warn("中立化 {} 失败：{}", mob.getType(), e.toString());
        }
        return EventResult.pass();
    }

    /** 供测试/外部访问分派表。 */
    public StrategyRegistry registry() {
        return registry;
    }
}
