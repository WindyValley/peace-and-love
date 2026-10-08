package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.EntityType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import top.windyvalley.peaceandlove.config.ConfigManager;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

/**
 * NeutralizationService 的组装正确性。
 *
 * <p>服务的核心价值是「按正确顺序组装策略表」：BrainBased 特例必须先于
 * GoalBased 兜底注册，否则 Brain 系生物会落入 GoalBased 而拦截失效。
 * 这一组装逻辑可在 JUnit 验证。
 *
 * <p><b>未覆盖</b>：onEntityAdd 依赖服务端运行时
 * （Level、实体、事件触发），移交真机。
 */
class NeutralizationServiceAssemblyTest {

    @TempDir
    Path dir;

    @BeforeAll
    static void bootstrap() {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
    }

    private NeutralizationService newService() {
        return new NeutralizationService(new ConfigManager(dir));
    }

    @Test
    void 策略表含两个策略() {
        assertEquals(2, newService().registry().size());
    }

    @Test
    void Brain系分派到BrainBased() {
        NeutralizationService s = newService();
        assertInstanceOf(BrainBasedStrategy.class,
                s.registry().strategyFor(EntityType.PIGLIN),
                "猪灵应命中 BrainBased 而非 GoalBased 兜底");
        assertInstanceOf(BrainBasedStrategy.class,
                s.registry().strategyFor(EntityType.WARDEN));
    }

    @Test
    void Goal系分派到GoalBased() {
        NeutralizationService s = newService();
        assertInstanceOf(GoalBasedStrategy.class,
                s.registry().strategyFor(EntityType.ZOMBIE));
    }

    @Test
    void 服务构造不依赖运行时环境() {
        // 能成功 new 出来即证明组装路径无副作用（不碰 Level/事件）
        newService();
    }
}
