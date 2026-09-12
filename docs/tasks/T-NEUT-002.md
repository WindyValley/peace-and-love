# T-NEUT-002: GoalBasedStrategy（32 个 Goal 系）

**状态：** todo
**优先级：** P0
**预估：** 6h
**Owner：** agent
**依赖：** T-NEUT-001
**可并行：** T-NEUT-003

## 目标

对 32 个 Goal 系生物移除攻击类 Goal 与索敌类 TargetGoal。

## 来源

- 设计：`../02-design.md` §3.5
- 决策：`../adr/004`

## 验收标准

- [ ] 用 `goalSelector.removeAllGoals(Predicate)` 移除攻击 Goal
- [ ] 用 `targetSelector.removeAllGoals(Predicate)` 移除索敌 Goal
- [ ] 移除前快照，支持 `restore()`
- [ ] **保留** `HurtByTargetGoal`（受击反击是设计要求）
- [ ] 生物不再主动接近/攻击玩家
- [ ] 移除操作幂等（重复调用不产生副作用）

## 技术要点

`GoalSelector.removeAllGoals(Predicate<Goal>)` **存在且 public**（spike 字节码验证）。

需移除的 Goal 类型：
- `MeleeAttackGoal` / `RangedAttackGoal` / `RangedBowAttackGoal` / `RangedCrossbowAttackGoal`
- `NearestAttackableTargetGoal`（索敌玩家的那条）

**不要移除** `HurtByTargetGoal` —— 受击反击由 ANGER 模块统一控制。

## 产出物

- 代码：`neutralize/GoalBasedStrategy.java`
- Commit：`feat(neutralize): 实现 Goal 系中立化策略`

## 备注

无
