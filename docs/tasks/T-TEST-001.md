- [x] T-TEST-001: 单元测试：定价引擎

**完成备注：** 2026-10-13：新增 PricingGoldenTest（golden/final_pricing_128.json 由 Gradle 从 spike 复制，单一真相不入测试树），110 条 price_128/price_64 零误差+关键锚点+同生物单调+0/11 边界。黄金比对抓出 Java Math.round(半数进位) 与 Python round(HALF_EVEN) 差异：仅 rabbit/rabbit_foot(epk0.1,pos 恰 0.5) 1 条 65/33 vs 64/32；PricingEngine 改 Math.rint 对齐，兔子非适配怪、70 在售价零影响。common 203 全绿
**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-PRICE-004
**可并行：** T-TEST-002, T-TEST-003

## 目标

以 spike 产出的 `final_pricing_128.json` 为黄金基准，验证定价实现一致。

## 来源

- 数据：`spikes/design-verify/final_pricing_128.json`

## 验收标准

- [x] 110 条目逐条比对价格，允许 ±0 误差（整数）
- [x] 关键锚点：僵尸铁锭 **117**、凋灵骷髅头颅 **94**、铜锭 **62**、末影珍珠 **30**、腐肉 **16**、女巫红石 **1**
- [x] 单调性断言：110/110
- [x] 边界：0 撞上限、11 撞下限
- [x] 改 `price_max` 后曲线仍单调

## 技术要点

黄金基准由 Python spike 产出，Java 实现必须复现同样数值。
若不一致，先确认是 Java 实现错误还是 spike 算法有误，**不要直接改基准**。

## 产出物

- 测试：`PricingGoldenTest.java`
- Commit：`test(pricing): 添加定价黄金基准测试`

## 备注

无
