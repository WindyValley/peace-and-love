- [x] T-NEUT-001: NeutralizeStrategy 接口与 GoalSnapshot

**完成备注：** commit 42a0a7f；NeutralizationStrategy 接口（卡初名 NeutralizeStrategy，落地改名）+ GoalSnapshot + StrategyRegistry，GoalSnapshotAndRegistryTest 覆盖
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SCOPE-002
**可并行：** T-TRADE-001

## 目标

定义中立化策略接口与 Goal 快照结构，为可逆还原打基础。

## 来源

- 设计：`../02-design.md` §3.5 中立化策略
- 决策：`../adr/004`

## 验收标准

- [x] `NeutralizationStrategy`（任务卡初名 NeutralizeStrategy，落地改名）含 `neutralize(Mob)` / `restore(Mob)` / `supports(EntityType)`
- [x] `GoalSnapshot` 记录被移除 Goal 的 `priority` + `Goal` 实例
- [x] 快照可原样恢复到 `GoalSelector`
- [x] 策略注册表按 EntityType 分派

## 技术要点

`WrappedGoal.getGoal()` 与 `getPriority()` 均为 **public**（spike 已验证），
因此无需反射即可做快照。

```java
record GoalSnapshot(int priority, Goal goal) {}
```

## 产出物

- 代码：`neutralize/NeutralizeStrategy.java`、`neutralize/GoalSnapshot.java`
- Commit：`feat(neutralize): 定义中立化策略接口`

## 备注

无
