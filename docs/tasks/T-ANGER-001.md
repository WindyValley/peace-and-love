# T-ANGER-001: LivingEntityHurtMixin 仇恨注入点

**状态：** done
**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-NEUT-001
**可并行：** T-TRADE-003

## 目标

在受伤事件注入，**只有玩家攻击**才触发仇恨，其余伤害源一律不介入。

## 来源

- 设计：`../02-design.md` §4.2 仇恨触发点
- 需求：FR-1.2（用户两次强调的硬约束）

## 验收标准

- [ ] 注入 `LivingEntity#hurt(DamageSource, float)`
- [ ] **玩家直接攻击** → 触发仇恨
- [ ] **玩家投射物**（箭/雪球/三叉戟等）→ 触发仇恨
- [ ] **玩家点燃的 TNT / 苦力怕爆炸** → 触发仇恨（爆炸源可追溯到玩家时）
- [ ] **玩家的宠物**（owner 为玩家的狼/猫等）→ 触发仇恨
- [ ] ❌ 铁傀儡攻击 → **不触发**
- [ ] ❌ 村民卫兵攻击 → **不触发**
- [ ] ❌ 其他怪物攻击（怪物内斗）→ **不触发**
- [ ] ❌ 环境伤害（跌落/岩浆/窒息/仙人掌）→ **不触发**
- [ ] 单测覆盖上述 9 种情况

## 技术要点

**这是全项目语义最敏感的判定**，用户两次强调，务必逐条落实。

伤害源溯源：
```java
Entity direct = source.getDirectEntity();   // 箭
Entity attacker = source.getEntity();       // 射箭的玩家
```

判定链：
1. `attacker instanceof Player` → ✅
2. `attacker instanceof TamableAnimal t && t.getOwner() instanceof Player` → ✅
3. `attacker instanceof PrimedTnt tnt && tnt.getOwner() instanceof Player` → ✅
4. 其余 → ❌ 完全不介入，走原版逻辑

`Entity.hurt(DamageSource,float)` 1.21.1 混淆名为 `a`（spike 已确认）。

## 产出物

- 代码：`mixin/LivingEntityHurtMixin.java`
- 测试：`HurtSourceTest.java`（9 种伤害源）
- Commit：`feat(anger): 实现仇恨触发点（仅玩家攻击）`

## 备注

⚠️ 用户明确强调过两次的硬约束，实现后必须逐条真机验证。
**完成时间：** 2026-09-14
**Commit：** 2d22f7d
**备注：** 反击与示警已解耦：生物间攻击仍走正常反击，玩家攻击才触发同族示警
