package top.windyvalley.peaceandlove.pricing;

import net.minecraft.world.level.storage.loot.providers.number.BinomialDistributionGenerator;
import net.minecraft.world.level.storage.loot.providers.number.ConstantValue;
import net.minecraft.world.level.storage.loot.providers.number.UniformGenerator;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** {@link NumberExpectations} 纯数学测试（不依赖注册表/上下文）。 */
class NumberExpectationsTest {

    private static final double EPS = 1e-9;

    @Test
    void 常量_provider_期望即其值() {
        assertEquals(3.0, NumberExpectations.expected(ConstantValue.exactly(3.0F)), EPS);
    }

    @Test
    void 均匀分布_期望为中点() {
        // uniform(0,2) -> 1
        assertEquals(1.0,
                NumberExpectations.expected(UniformGenerator.between(0.0F, 2.0F)), EPS);
        // 女巫掉落棍数 uniform(0,1) 的 rolls 等
        assertEquals(0.5,
                NumberExpectations.expected(UniformGenerator.between(0.0F, 1.0F)), EPS);
    }

    @Test
    void 二项分布_期望为_n_乘_p() {
        // binomial(n=4,p=0.5) -> 2
        assertEquals(2.0,
                NumberExpectations.expected(BinomialDistributionGenerator.binomial(4, 0.5F)), EPS);
    }

    @Test
    void set_count_均匀分布_按整数逐值_clamp_到非负() {
        // spike 缺陷②：uniform(0,2) 逐整数 {0,1,2} 平均 = 1
        assertEquals(1.0,
                NumberExpectations.expectedCountClamped(UniformGenerator.between(0.0F, 2.0F)), EPS);
        // uniform(-1,1) 逐整数 clamp 后 {0,0,1} 平均 = 1/3，而不是 ( -1+1)/2=0
        assertEquals(1.0 / 3.0,
                NumberExpectations.expectedCountClamped(UniformGenerator.between(-1.0F, 1.0F)), EPS);
        // uniform(0,1) -> {0,1} 平均 0.5（与直接中点一致）
        assertEquals(0.5,
                NumberExpectations.expectedCountClamped(UniformGenerator.between(0.0F, 1.0F)), EPS);
    }

    @Test
    void set_count_常量_负值_clamp_为零() {
        assertEquals(0.0,
                NumberExpectations.expectedCountClamped(ConstantValue.exactly(-2.0F)), EPS);
        assertEquals(2.0,
                NumberExpectations.expectedCountClamped(ConstantValue.exactly(2.0F)), EPS);
    }

    @Test
    void 数量上界_取_floor_max_且至少为1() {
        assertEquals(2, NumberExpectations.maxCount(UniformGenerator.between(0.0F, 2.0F)));
        assertEquals(1, NumberExpectations.maxCount(ConstantValue.exactly(1.0F)));
        assertEquals(1, NumberExpectations.maxCount(UniformGenerator.between(0.0F, 0.0F)));
        assertEquals(4, NumberExpectations.maxCount(BinomialDistributionGenerator.binomial(4, 0.5F)));
    }
}
