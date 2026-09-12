# T-NEUT-007: 特殊适配 C 组（末影人 + 僵尸猪灵）

**状态：** todo
**优先级：** P0
**预估：** 5h
**Owner：** agent
**依赖：** T-NEUT-002
**可并行：** T-NEUT-005, T-NEUT-006

## 目标

处理两个原版已实现 `NeutralMob` 的生物，避免原版机制与模组逻辑重叠。

## 来源

- 验证：`../P1-P4-VERIFY.md` P4（本任务由 P4 验证新发现）
- 决策：`../adr/004`

## 验收标准

- [ ] **末影人**：禁用凝视激怒（`isLookingAtMe` / `setBeingStaredAt`）
- [ ] 玩家看末影人不再触发攻击（凝视属主动索敌，非「受玩家攻击」）
- [ ] 末影人瞬移、搬方块等非攻击行为保持原版
- [ ] **僵尸猪灵**：禁用原版群体报复（`customServerAiStep` 内）
- [ ] 群体报复改由 `KinAlerter` 统一接管（4 格 / 单层 / 禁链式）
- [ ] 验证不出现「双份示警」导致范围失控
- [ ] 两者已实现的 5 个 `NeutralMob` 方法**可复用**，不重复实现存储层
- [ ] 真机验证：攻击一只僵尸猪灵，确认只有 4 格内同类被激怒且不再扩散

## 技术要点

**本任务源于 P4 验证的意外发现** —— 原设计以为猪灵系已实现 `NeutralMob`，
实测是末影人与僵尸猪灵（都是 Goal 系）。

两者均**未调用** `forgetCurrentTargetAndRefreshUniversalAnger()`，
所以「仇恨不扩散到其他玩家」不会被原版破坏，这是好消息。

但**僵尸猪灵的群体报复与 KinAlerter 功能重叠**，必须二选一，
否则一次攻击触发两套传播逻辑，范围会远超 4 格。

## 产出物

- 代码：`neutralize/special/EndermanAdapter.java`、`ZombifiedPiglinAdapter.java`
- Commit：`feat(neutralize): 末影人与僵尸猪灵特殊适配`

## 备注

P4 验证新增任务，原设计文档中不存在。
