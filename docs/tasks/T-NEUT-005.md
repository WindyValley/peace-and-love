- [x] T-NEUT-005: 特殊适配 A 组（袭击系 + 潜影贝 + 幻翼）

**优先级：** P0
**预估：** 8h
**Owner：** agent
**依赖：** T-NEUT-002
**可并行：** T-NEUT-006, T-NEUT-007

## 目标

处理 6 个行为特殊的生物：潜影贝、幻翼、掠夺者、卫道士、唤魔者、恼鬼。

## 来源

- 设计：`../02-design.md` §3.5 特殊适配
- 决策：`../adr/004`

## 验收标准

> **2026-10-13 源码实证修订**：逐条核对 1.21.1 源码后，原卡多数担心点已被通用
> GoalBasedStrategy 覆盖（索敌均为 targetSelector 中的 TargetGoal 子类，中立化即删）。
> 唯一代码缺口是**幻翼**（索敌器是裸 `Goal`，旧谓词漏网），已通过谓词收窄修复。
> 详见 `../02-design.md §3.5.1`。勾选项=代码已闭环；真机项待 98 服实测。

- [x] **潜影贝**：索敌（ShulkerNearestAttackGoal/DefenseAttackGoal，均 NearestAttackable 子类）已随通用策略删除。`ShulkerAttackGoal` 是 **goalSelector 的攻击执行器（非索敌），按架构保留**（被打反击要射子弹），固定方块/附着特性不变（原卡「移除 ShulkerAttackGoal」措辞有误，实证修正）
- [x] **幻翼**：`PhantomAttackPlayerTargetGoal extends Goal`（裸 Goal，非 TargetGoal）原被旧谓词漏掉；谓词收窄为「targetSelector 除 HurtByTargetGoal 外全删」后已移除。不睡眠仍会生成（生成条件不碰），但不再索敌俯冲；俯冲攻击执行器 PhantomSweepAttackGoal 依赖 getTarget，无目标不触发
- [x] **掠夺者/卫道士/唤魔者**：主动索敌全是 NearestAttackableTargetGoal，已删；共享 `Raider` 基类注册的 PathfindToRaid/MoveThroughVillage/Celebration 等在 **goalSelector（移动，非索敌）保留**，袭击寻路/参与能力不变
- [x] **唤魔者**：`EvokerSummonSpellGoal.canUse()` 要求 `getTarget()!=null`，中立无目标 → 不施法、不召唤恼鬼（无需额外代码）
- [x] **恼鬼**：`VexCopyOwnerTargetGoal extends TargetGoal`（复制 owner 目标）已删；唤魔者召唤出的恼鬼经 `addFreshEntity` 触发 EntityEvent.ADD，被中立化服务自动中立化（owner 中立→恼鬼中立）
- [x] 袭击（Raid）事件中这些生物**仍会生成**（生成逻辑不碰），但无主动索敌 goal 不主动攻击
- [x] Johnny 卫道士：`VindicatorJohnnyAttackGoal extends NearestAttackableTargetGoal`，已随通用策略删除（改名 Johnny 也不主动攻击）
- [x] **逐个真机验证**（2026-10-14，98 服 NeoForge + mc-client-rpc）：`verify_neut005_phantom.py` 幻翼移出白名单后自由飞 14s 不俯冲/不掉血/source=NONE，打后 PLAYER_DIRECT 并俯冲反击（20→18.8），白名单已还原；`verify_neut005_regression.py` 对 shulker / Johnny / 普通 vindicator / pillager / evoker / vex 6 种（均临时移出白名单）两阶段全过——A 不主动（NONE/none/不掉血）、B 命中 PLAYER_DIRECT 且 target=player（反击门控放行）。注：回归脚本用抗性 10 保命，掉血仅旁证；shulker/Johnny 在无抗性轮已实测真掉血（20→13.8、Johnny 一斧击杀）

## 技术要点

⚠️ **风险任务**：三个袭击系生物共享 `Raider` 基类，改动易互相影响。
建议单独开分支 `feat/special-raiders`，逐个验证后合并。

袭击机制的语义问题：袭击本身是「敌对事件」，但生物已中立化。
设计决策：**保留袭击生成，但生物不主动攻击**（村民与铁傀儡仍会攻击它们，
这属于 NPC 互斗，模组不介入）。

## 产出物（2026-10-13 实际落地）

- 无独立 Adapter 类（源码实证后不需要）。
- `common/.../neutralize/GoalBasedStrategy.java`：移除谓词收窄为「targetSelector 除 HurtByTargetGoal 外全删」，覆盖幻翼裸 Goal 索敌器（本组唯一代码缺口）。
- 潜影贝/三袭击系/恼鬼/Johnny 均由该通用策略 + 既有 KinAlerter/HurtByTargetGoalMixin 覆盖。
- Commit：本分支 `feat/special-mobs-neut-005-007`（按 NEUT-005/006/007 分批提交）。

## 备注

⚠️ 风险任务：`Raider` 基类共享，需单独分支 + 逐个真机验证。
