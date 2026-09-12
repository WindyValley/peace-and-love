# T-TRADE-004: RestockManager 每日补货

**状态：** todo
**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-TRADE-002
**可并行：** T-TRADE-005

## 目标

每游戏日重置交易次数，自写 `resetAllUses()`，禁用 `Villager.restock()`。

## 来源

- 设计：`../02-design.md` §5.3 每日补货
- 决策：`../adr/003`

## 验收标准

- [ ] 游戏日推进时（24000 tick）重置所有 offer 的 uses
- [ ] `restock_interval_days` 支持小数（如 0.5 = 半天）
- [ ] **不得调用 `Villager.restock()`**（会引入 gossip/demand 副作用）
- [ ] 补货判定基于 `level.getGameTime()`，非真实时间
- [ ] 玩家不在线期间的补货在实体加载时补算

## 技术要点

```java
long currentDay = level.getGameTime() / 24000L;
if (currentDay - pal$lastRestockDay >= intervalDays) {
    offers.forEach(MerchantOffer::resetUses);   // 自写，非 restock()
    pal$lastRestockDay = currentDay;
}
```
`resetUses()` 是 `MerchantOffer` 的 public 方法，spike 已验证存在。

## 产出物

- 代码：`trade/RestockManager.java`
- 测试：`RestockManagerTest.java`（边界：跨日、小数间隔）
- Commit：`feat(trade): 实现每日补货机制`

## 备注

无
