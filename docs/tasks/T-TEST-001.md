- [ ] T-TEST-001: 单元测试：定价引擎

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

- [ ] 110 条目逐条比对价格，允许 ±0 误差（整数）
- [ ] 关键锚点：僵尸铁锭 **117**、凋灵骷髅头颅 **94**、铜锭 **62**、末影珍珠 **30**、腐肉 **16**、女巫红石 **1**
- [ ] 单调性断言：110/110
- [ ] 边界：0 撞上限、11 撞下限
- [ ] 改 `price_max` 后曲线仍单调

## 技术要点

黄金基准由 Python spike 产出，Java 实现必须复现同样数值。
若不一致，先确认是 Java 实现错误还是 spike 算法有误，**不要直接改基准**。

## 产出物

- 测试：`PricingGoldenTest.java`
- Commit：`test(pricing): 添加定价黄金基准测试`

## 备注

无
