- [x] T-TEST-003: 单元测试：补货周期边界

**完成备注：** 2026-10-13：补存档回滚容错用例（锚点 gameTime/day 都在未来→不崩不误补、锚点不回拨），RestockManagerTest 6/6
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

- [x] 游戏时间 23999 → 24000 触发补货
- [x] `restock_interval_days=0.5` → 12000 tick 补一次
- [x] 离线 100 天后加载 → 只补一次（非补 100 次）
- [x] `lastRestockDay` 未来时间（存档回滚）→ 容错不崩
- [x] 补货后 `maxUses` 恢复为 1
- [x] **不调用** `Villager.restock()`（勘误 2026-10-13：未写 spy——以「common 全仓零 `.restock(` 调用点 + RestockManager 纯算术不持有 Mob」作静态保证，补货只调 `MerchantOffer.resetUses()`）

## 技术要点

用假的 `gameTime` 注入，不依赖真实服务端。

## 产出物

- 测试：`RestockManagerTest.java`
- Commit：`test(trade): 添加补货边界测试`

## 备注

无
