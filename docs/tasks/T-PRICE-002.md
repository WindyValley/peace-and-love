# T-PRICE-002: PriceCalculator 对数曲线

**状态：** todo
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-PRICE-001
**可并行：** T-CFG-003

## 目标

实现 epk → 价格的对数映射曲线。

## 来源

- 设计：`../02-design.md` §3.3
- 决策：`../adr/003`

## 验收标准

- [ ] `pos = log(epk_cheap/epk) / log(epk_cheap/epk_rare)`
- [ ] `price = 1 + (price_max-1) × pos`，clamp 到 [1, price_max]
- [ ] `epk_cheap` / `epk_rare` / `price_max` 全部从配置读取
- [ ] 单调性：epk 越小价格越高
- [ ] 边界：epk ≥ cheap 时价格 = 1；epk ≤ rare 时价格 = price_max

## 技术要点

分母 `log(2/0.005) ≈ 5.99`（默认参数）。
用 `Math.log` 而非 `Math.log10`，两者比值等价但保持与 spike 一致。
结果取整用 `Math.round`。

## 产出物

- 代码：`pricing/PriceCalculator.java`
- 测试：`PriceCalculatorTest.java`
- Commit：`feat(pricing): 实现对数定价曲线`

## 备注

无
