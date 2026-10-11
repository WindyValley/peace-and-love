- [ ] T-NEUT-004: restore() 可逆还原

**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-NEUT-002, T-NEUT-003
**可并行：** T-TRADE-005

## 目标

白名单移入时把生物还原为原版行为，保证配置热重载完全可逆。

## 来源

- 设计：`../02-design.md` §3.5
- 需求：FR-1.4（用户确认可逆为必需）

## 验收标准

- [ ] Goal 系从快照恢复 Goal 与 priority
- [ ] Brain 系停止 memory 擦除
- [ ] 还原后生物行为与原版**完全一致**
- [ ] 还原后交易能力移除（右键无反应）
- [ ] 反复 neutralize/restore 10 次无状态泄漏
- [ ] 真机验证：加白名单 → reload → 生物恢复攻击

## 技术要点

快照存在实体上（`@Unique` 字段）而非全局 Map，避免实体卸载后泄漏。
若快照丢失（如实体重新加载），退化为「重建原版 Goal」——需要为每个生物类型
记录其原版 Goal 构造方式，成本高。**优先保证快照不丢**：neutralize 在实体
`finalizeSpawn` 或首次 tick 时执行，快照随实体生命周期存在。

## 产出物

- 代码：`neutralize/GoalBasedStrategy.java`、`BrainBasedStrategy.java`
- Commit：`feat(neutralize): 实现可逆还原`

## 备注

无
