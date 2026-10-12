- [x] T-NEUT-003: BrainBasedStrategy（6 个 Brain 系）

**完成备注：** commit 8967fab + 44ff721；覆盖 Brain 6 生物，机制由每tick擦除重构为 BrainMixin 写入源头拦截（验收已勘误），BrainBasedStrategyTest + BrainTickPerfSmokeTest；猪灵/疣猪兽同族示警真机（test_brain_kin_alert）
**优先级：** P0
**预估：** 6h
**Owner：** agent
**依赖：** T-NEUT-001
**可并行：** T-NEUT-002

## 目标

对 6 个 Brain 系生物每 tick 擦除 `ATTACK_TARGET` memory。

## 来源

- 设计：`../02-design.md` §5.2 Brain 系每 tick 拦截
- 决策：`../adr/004`

## 验收标准

- [x] 覆盖猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽/监守者/旋风人
- [x] 攻击记忆在**写入源头**拦截：BrainMixin 于 setMemoryInternal 按 BrainAttackGate 门控取消 ATTACK_TARGET（猪灵族另拦 ANGRY_AT），取代旧的每 tick 擦除（commit 44ff721）
- [x] 玩家攻击产生的愤怒/反击记忆在门控处放行（允许反击）
- [x] `restore()` 随白名单门控停止拦截（Brain 系无 Goal 结构改动，空操作）
- [x] 无每 tick 全服扫描；BrainTickPerfSmokeTest 做性能基线

## 技术要点

```java
brain.eraseMemory(MemoryModuleType.ATTACK_TARGET);
brain.eraseMemory(MemoryModuleType.ANGRY_AT);   // 猪灵系
```

⚠️ **性能风险**（RISKS R?）：每 tick 拦截在大量实体时可能有开销。
先做基线：100 只生物同时加载，测 tick 耗时增量。超标改用事件驱动。

## 产出物

- 代码：`neutralize/BrainBasedStrategy.java`
- Commit：`feat(neutralize): 实现 Brain 系中立化策略`

## 备注

⚠️ 风险任务：性能需实测基线。
