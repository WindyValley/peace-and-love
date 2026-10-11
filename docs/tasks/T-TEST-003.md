- [ ] T-TEST-003: 单元测试：补货周期边界

**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-TRADE-004
**可并行：** T-TEST-001, T-TEST-002

## 目标

验证补货在跨日、小数间隔、长时间离线等边界下的正确性。

## 来源

- 设计：`../02-design.md` §5.3

## 验收标准

- [ ] 游戏时间 23999 → 24000 触发补货
- [ ] `restock_interval_days=0.5` → 12000 tick 补一次
- [ ] 离线 100 天后加载 → 只补一次（非补 100 次）
- [ ] `lastRestockDay` 未来时间（存档回滚）→ 容错不崩
- [ ] 补货后 `maxUses` 恢复为 1
- [ ] **不调用** `Villager.restock()`（用 spy 断言）

## 技术要点

用假的 `gameTime` 注入，不依赖真实服务端。

## 产出物

- 测试：`RestockManagerTest.java`
- Commit：`test(trade): 添加补货边界测试`

## 备注

无
