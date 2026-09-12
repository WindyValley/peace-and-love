package top.windyvalley.peaceandlove.neutralize;

import dev.architectury.event.EventResult;
import dev.architectury.event.events.common.EntityEvent;
import dev.architectury.event.events.common.TickEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.config.ConfigManager;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

/**
 * 中立化接线服务 —— 把策略挂到服务端运行时。
 *
 * <p>两个挂点：
 * <ol>
 *   <li>{@code EntityEvent.ADD}：实体加入世界时，若门控判定「中立化生效」，
 *       按策略 neutralize。Goal 系在此一次性移除 Goal 即完成；
 *       Brain 系此处做一次初始清理。</li>
 *   <li>{@code TickEvent.SERVER_LEVEL_POST}：每 tick 遍历 Brain 系已适配生物，
 *       擦除攻击记忆（Brain 系的持续生效点）。Goal 系不需要每 tick 处理，
 *       故只遍历 Brain 系，控制开销。</li>
 * </ol>
 *
 * <p><b>门控在挂点入口判定</b>：事件里对每个实体先过
 * {@link NeutralizationScope#isNeutralized}，白名单/未适配的直接跳过——
 * 白名单热重载后，新进入的生物自然按新门控走，已中立化的由
 * {@code /pal reload} 触发的 restore 流程还原（后续任务）。
 *
 * <p><b>⚠️ 验证方式</b>：事件的实际触发、Mixin 注入、策略对真实 Mob 的
 * 效果，均依赖服务端运行时，无法用纯 JUnit 验证。本类标注「已写未验」，
 * 待部署到测试服务端后真机验证。
 */
public final class NeutralizationService {

    private final StrategyRegistry registry;
    private final BrainBasedStrategy brainStrategy;
    private final ConfigManager config;

    public NeutralizationService(ConfigManager config) {
        this.config = config;
        this.registry = new StrategyRegistry();
        this.brainStrategy = new BrainBasedStrategy();
        // BrainBased 特例先于 GoalBased 兜底注册
        this.registry.register(brainStrategy)
                .register(new GoalBasedStrategy());
    }

    /** 注册事件监听，由 {@code PeaceAndLove.init()} 调用。 */
    public void register() {
        EntityEvent.ADD.register(this::onEntityAdd);
        TickEvent.SERVER_LEVEL_POST.register(this::onLevelTick);
        PeaceAndLove.LOGGER.info("中立化服务已接线（EntityEvent.ADD + SERVER_LEVEL_POST）");
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
            // 单个实体失败不应拖垮 tick；记日志后继续
            PeaceAndLove.LOGGER.warn("中立化 {} 失败：{}", mob.getType(), e.toString());
        }
        return EventResult.pass();
    }

    /** 每 tick：擦除 Brain 系已适配生物的攻击记忆。 */
    private void onLevelTick(ServerLevel level) {
        // 只遍历 Brain 系：Goal 系在 ADD 时已一次性移除，无需每 tick
        for (Entity entity : level.getAllEntities()) {
            if (!(entity instanceof Mob mob)) {
                continue;
            }
            if (!brainStrategy.supports(mob.getType())) {
                continue;
            }
            if (!NeutralizationScope.isNeutralized(mob.getType(), config.get())) {
                continue;
            }
            brainStrategy.tick(mob);
        }
    }

    /** 供测试/外部访问分派表。 */
    public StrategyRegistry registry() {
        return registry;
    }

    /** 供 AngerController 接线 anger 探针。 */
    public BrainBasedStrategy brainStrategy() {
        return brainStrategy;
    }
}
