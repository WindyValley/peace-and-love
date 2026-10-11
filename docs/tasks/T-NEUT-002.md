- [x] T-NEUT-002: GoalBasedStrategy（32 个 Goal 系）

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

- [x] ~~用 `goalSelector.removeAllGoals(Predicate)` 移除攻击 Goal~~ **已推翻（见备注）——攻击 Goal 保留**
- [x] 用 `targetSelector.removeAllGoals(Predicate)` 移除主动索敌 Goal
- [x] 移除前快照，支持 `restore()`
- [x] **保留** `HurtByTargetGoal`（受击反击是设计要求）
- [x] **保留** 攻击 Goal（`MeleeAttackGoal` 等）——负责寻路+攻击执行
- [x] 生物不再主动接近/攻击玩家
- [x] 移除操作幂等（重复调用不产生副作用）

## 技术要点

`GoalSelector.removeAllGoals(Predicate<Goal>)` **存在且 public**（spike 字节码验证）。

**只移除** `targetSelector` 中「非 `HurtByTargetGoal`」的 `TargetGoal`
（`NearestAttackableTargetGoal`、`OwnerHurtTargetGoal`、`DefendVillageTargetGoal` 等主动索敌）。

**不要移除**：
- `HurtByTargetGoal` —— 受击反击由 ANGER 模块统一控制。
- `MeleeAttackGoal` / `RangedAttackGoal` 等攻击 Goal —— 它们只在
  `mob.getTarget() != null` 时激活，负责寻路到目标并攻击。

## ⚠️ 设计修正（2026-09-14，真机验证发现的根因）

原设计「同时移除攻击 Goal」是**错的**，真机表现为「被打不反击」：

`HurtByTargetGoal` 构造时 `super(mob, true)` → `mustReach=true` →
`canAttack()` 内部调 `canReach()` → `mob.getNavigation().createPath()`。
攻击 Goal（如 `ZombieAttackGoal`）被删后，没有任何 Goal 驱动 `navigation`，
`createPath()` 返回 null 或路径终点偏移 → `canAttack()` 返回 false →
`HurtByTargetGoal.canUse()` 永远 false → 僵尸被打不反击。

**修正**：参考末影人/北极熊/熊猫的原版实现——中立生物**保留攻击 Goal**，
只删主动索敌 Goal。攻击 Goal 不会主动索敌，只跟随 `targetSelector` 设定的目标。

**真机验证**（服务端 JSON-RPC + runClient 离线直连）：真实玩家 Dev（生存）上线，
`player.attack` 打僵尸后日志出现 `Dev was slain by Zombie` —— 反击链生效。

## 产出物

- 代码：`neutralize/GoalBasedStrategy.java`、`verify/JsonRpcService.java`（验证设施）
- Commit：
  - `b9c262b fix(neutralize): 保留攻击Goal修复被打不反击`
  - `2de1789 feat(verify): 服务端 JSON-RPC 验证设施 + runClient 离线直连`

## 备注

客户端侧 JSON-RPC（真实输入驱动，操控玩家实体做完整攻击/移动/视角动作）
另立独立项目，不在本任务范围。服务端 JSON-RPC 设施硬编码开启、无鉴权，
正式发布前必须关闭或移除。
