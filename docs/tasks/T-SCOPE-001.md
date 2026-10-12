- [x] T-SCOPE-001: AdaptedMobs 38 个常量

**完成备注：** commit bd3a95b；AdaptedMobsTest 断言合计38（GOAL_BASED 32 + BRAIN_BASED 6，第六为旋风人 BREEZE），集合不可变、O(1)，末影龙不在
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SETUP-003
**可并行：** T-CFG-001

## 目标

定义 v1.0 已适配的 38 个生物常量，按 Goal(32)/Brain(6) 分组，不可变。

## 来源

- 设计：`../02-design.md` §3.2 已适配生物列表
- 数据：`spikes/r3-ai/neutralization_plan_v3.json`

## 验收标准

- [x] `AdaptedMobs.GOAL_BASED` 含 32 个 EntityType
- [x] `AdaptedMobs.BRAIN_BASED` 含 6 个：猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽/监守者/旋风人
- [x] 合计 38，且 `isAdapted(EntityType)` 查询为 O(1)
- [x] **末影龙不在列表中**
- [x] 集合为不可变（`Set.copyOf` 或 `ImmutableSet`）
- [x] 单测断言总数 == 38

## 技术要点

从 `neutralization_plan_v3.json` 生成，**不要手敲**，避免拼写错误。
注意类名与 entity id 不一致的特例：`WitherBoss`→`wither`、`EnderMan`→`enderman`。

## 产出物

- 代码：`scope/AdaptedMobs.java`
- 测试：`AdaptedMobsTest.java`
- Commit：`feat(scope): 定义 38 个已适配生物常量`

## 备注

无
