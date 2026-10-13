- [ ] T-NEUT-006: 特殊适配 B 组（凋灵 + 监守者）

**优先级：** P0
**预估：** 5h
**Owner：** agent
**依赖：** T-NEUT-002, T-NEUT-003
**可并行：** T-NEUT-005, T-NEUT-007

## 目标

处理两个 Boss/准 Boss：凋灵（硬编码索敌）与监守者（Brain 系 + 振动感知）。

## 来源

- 设计：`../02-design.md` §10 凋灵的处理
- 决策：`../adr/004`（凋灵移出默认白名单）

## 验收标准

- [ ] **凋灵**：`customServerAiStep()` 内硬编码索敌需 Mixin 拦截
- [ ] 凋灵默认**被中立化**（不在默认白名单）
- [ ] `boss_trading_enabled=false` 时凋灵中立但不开交易界面
- [ ] 凋灵不再主动发射头颅攻击玩家
- [ ] 凋灵召唤时的爆炸/破坏行为保持原版（非攻击行为）
- [ ] **监守者**：Brain 系，禁用振动感知触发的索敌
- [ ] 监守者的 Sonic Boom 不再对玩家释放
- [ ] 监守者默认被中立化（不在默认白名单）
- [ ] 两者真机验证

## 技术要点

**凋灵**的索敌不走标准 `TargetGoal`，在 `WitherBoss#customServerAiStep()` 内硬编码，
必须用 Mixin `@Inject` 拦截，不能靠 `removeAllGoals`。

**监守者**是 Brain 系，但额外有 `VibrationSystem` 接口，
振动感知会触发 `MemoryModuleType.DISTURBANCE_LOCATION` → 索敌。
需同时擦除该 memory。

## 产出物

- 代码：`neutralize/special/WitherAdapter.java`、`WardenAdapter.java`
- Commit：`feat(neutralize): 凋灵与监守者特殊适配`

## 备注

无
