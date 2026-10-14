- [x] T-NEUT-007: 特殊适配 C 组（末影人 + 僵尸猪灵）

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

> **2026-10-13 源码实证修订**：末影人凝视激怒全封装在 targetSelector 的
> `EndermanLookForPlayerGoal`（NearestAttackableTargetGoal 子类），已随通用策略删除，
> 无需独立 EndermanAdapter。僵尸猪灵确有独立于 HurtBy 链的第二条大范围传染，是真缺口，
> 由 `ZombifiedPiglinMixin` 拦截。详见 `../02-design.md §3.5.1`。勾选项=代码已闭环；
> 真机项待 98 服实测。

- [x] **末影人**：凝视索敌 `EndermanLookForPlayerGoal extends NearestAttackableTargetGoal`（isLookingAtMe/setBeingStaredAt 的唯一调用者）已随通用策略删除；无需单独 Mixin isLookingAtMe
- [x] 玩家看末影人不再触发攻击（凝视属主动索敌，goal 已删；它不是「受玩家攻击」）
- [x] 末影人瞬移、搬方块、受惊/中箭瞬移等非攻击行为在 goalSelector 与 hurt/aiStep 中，未被中立化触碰，保持原版
- [x] **僵尸猪灵**：`customServerAiStep → 私有 alertOthers()`（每 tick 按 FOLLOW_RANGE 35 格 setTarget 传染）由 `ZombifiedPiglinMixin` 在中立化且目标为玩家时取消
- [x] 群体报复改由 KinAlerter 统一接管（受击 HurtByTargetGoal.alertOthers 已由 HurtByTargetGoalMixin 改道，球形 4 格 / 严格同类 / 单层）；非玩家源（铁傀儡/怪物内斗）保留原版传染
- [x] 不出现「双份示警」：玩家源的 35 格原版传染被 Mixin 取消，只剩 KinAlerter 的 4 格单层
- [x] 两者 5 个 NeutralMob 方法（持久愤怒 UUID/计时）直接复用原版，模组未重复实现存储层（AngerController 走 NeutralMob 接口）
- [ ] **真机验证**（待做）：攻击一只僵尸猪灵，确认仅 4 格内同类被激怒、不外扩不链式；凝视末影人不激怒、打它仍反击

## 技术要点

**本任务源于 P4 验证的意外发现** —— 原设计以为猪灵系已实现 `NeutralMob`，
实测是末影人与僵尸猪灵（都是 Goal 系）。

**2026-10-13 源码实证修正**：两者类体内确实没有直接调用 `forgetCurrentTargetAndRefreshUniversalAnger()`，
但 targetSelector 里注册的 `ResetUniversalAngerTargetGoal`（裸 Goal 子类）在
`universalAnger` 游戏规则开启时会调用它（含「对所有玩家记仇」语义）。旧谓词只认
TargetGoal，漏删这个裸 Goal；本次谓词收窄后已一并删除，从目标层杜绝该扩散路径。

僵尸猪灵的群体报复有两条独立链：受击瞬间的 HurtByTargetGoal.alertOthers（已由
HurtByTargetGoalMixin 改道 KinAlerter），与 customServerAiStep 私有的 alertOthers
（35 格大范围，本任务 Mixin 拦截）。二者必须都收窄，否则双份示警范围失控。

## 产出物（2026-10-13 实际落地）

- 代码：`common/.../mixin/ZombifiedPiglinMixin.java`（拦 35 格 alertOthers）；
  末影人无新代码（凝视 goal 随通用策略删除）。
- 连带：`GoalBasedStrategy` 谓词收窄，删除两者的 ResetUniversalAngerTargetGoal。
- 注册：`common/src/main/resources/peaceandlove-common.mixins.json`。
- Commit：本分支 `feat/special-mobs-neut-005-007`。

## 备注

P4 验证新增任务，原设计文档中不存在。
