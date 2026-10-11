- [x] T-PRICE-002.1: 对数曲线纯逻辑：epk→绿宝石价（零依赖 L1）

**完成备注：** commit 87ed582；PricingEngine 纯逻辑 + PricingEngineTest 10 例全绿
**优先级：** P0
**预估：** 2h
**Owner：** agent
**依赖：** T-PRICE-001
**可并行：** T-CFG-003

## 目标

实现 epk → [1,max] 整数绿宝石价的对数映射纯函数，不依赖任何 Minecraft 类，可纯 JUnit 覆盖。

## 来源

- 设计：../02-design.md §3.3 定价引擎
- 决策：../adr/003
- 拆分自：T-PRICE-002

## 验收标准

- [x] pos = log(cheap/epk) / log(cheap/rare)，归一化到 [0,1]
- [x] price = clamp(round(1+(max-1)*pos), 1, max)，整数价
- [x] 单调性：epk 越小价格越高（相对 epk 单调不增）
- [x] 边界：epk≥cheap → 1；epk≤rare 或 epk≤0 → max
- [x] 锚点非法（max<1、锚点非正、cheap≤rare）抛 IllegalArgumentException
- [x] 纯 JUnit 覆盖，PricingEngine 不 import 任何 MC 类

## 技术要点

- 用 Math.log 而非 Math.log10（比值等价，与 spike 一致），取整 Math.round，钳制 Math.clamp
- L1 基础设施零 MC 依赖，便于为后续 MC 版本隔离差异

## 产出物

- 代码：pricing/PricingEngine.java
- 测试：PricingEngineTest.java（10 例）
- Commit：87ed582

## 备注

已落地，commit 87ed582；PricingEngineTest 10 例全绿
