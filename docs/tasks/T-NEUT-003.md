# T-NEUT-003: BrainBasedStrategy（6 个 Brain 系）

**状态：** todo
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

- [ ] 覆盖猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽/监守者/旋风人
- [ ] 每 tick 检查并擦除 `MemoryModuleType.ATTACK_TARGET`
- [ ] 仇恨状态下**不擦除**（允许反击）
- [ ] `restore()` 停止擦除
- [ ] 性能：单实体每 tick 开销 < 1μs，做基线测量

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
