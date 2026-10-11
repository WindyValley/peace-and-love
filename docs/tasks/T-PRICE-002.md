- [-] T-PRICE-002: PriceCalculator 对数曲线

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

## 子任务（状态由子任务聚合，勿手改本卡状态）

- [x] T-PRICE-002.1: 对数曲线纯逻辑：epk→绿宝石价（零依赖 L1）
- [ ] T-PRICE-002.2: 定价锚点接配置：epk_cheap/epk_rare/price_max 从配置读取

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
