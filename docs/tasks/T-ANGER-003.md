# T-ANGER-003: KinAlerter 同族示警

**状态：** done
**优先级：** P0
**预估：** 5h
**Owner：** agent
**依赖：** T-ANGER-002
**可并行：** T-ANGER-004

## 目标

被玩家攻击时，通知**同一 EntityType**、**球形 4 格内**的同类，且**禁止链式传播**。

## 来源

- 设计：`../02-design.md` §3.6
- 需求：FR-1.2

## 验收标准

- [ ] 半径 `kin_alert_radius=4.0`（可配置），**球形**非立方体
- [ ] 仅同一 `EntityType` 被通知（僵尸不通知骷髅）
- [ ] 被通知者仇恨目标 = **同一个攻击者**（非通知者）
- [ ] ❌ **禁止链式传播**：被通知者不再通知它的邻居
- [ ] NPC 攻击导致的受伤**不触发示警**
- [ ] 半径设为 0 时完全禁用示警
- [ ] 单测覆盖传播边界（4.0 格内/外、链式截断）
- [ ] 真机验证：攻击僵尸群中一只，确认只有 4 格内被激怒且不扩散

## 技术要点

⚠️ **风险任务**：「禁止链式传播」实现易出错。

实现方式：示警调用带 `boolean propagate` 参数
```java
void alert(Mob source, Player attacker, boolean propagate) {
    if (!propagate) return;              // 被通知者不再传播
    for (Mob kin : nearbyKin(source, radius)) {
        kin.setAnger(attacker);
        alert(kin, attacker, false);     // ★ 传 false，截断链式
    }
}
```

球形判定用 `distanceToSqr() <= radius*radius`，
不要用 `AABB.inflate()`（那是立方体，角上会多出 ~73% 体积）。

⚠️ 僵尸猪灵需先禁用原版群体报复（T-NEUT-007），否则双份传播。

## 产出物

- 代码：`anger/KinAlerter.java`
- 测试：`KinAlerterTest.java`
- Commit：`feat(anger): 实现同族示警（单层非链式）`

## 备注

⚠️ 风险任务：链式截断逻辑需单测重点覆盖。
**完成时间：** 2026-09-14
**Commit：** 1e59761
**备注：** 反击与示警已解耦：生物间攻击仍走正常反击，玩家攻击才触发同族示警
