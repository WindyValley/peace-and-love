- [x] T-NEUT-006: 特殊适配 B 组（凋灵 + 监守者）

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

> **2026-10-13 源码实证修订**：凋灵主头索敌其实是标准 `NearestAttackableTargetGoal`
> （已随通用策略删除，保留 HurtByTargetGoal 反击）；真正硬编码的是**两个侧头**，
> 由 `WitherBossMixin` 拦截。监守者 Sonic Boom/振动索敌只认 ATTACK_TARGET 记忆，
> 已被 0.0.2 的 BrainAttackGate 源头门控覆盖（曾真机双向全绿），本次零代码。
> 详见 `../02-design.md §3.5.1`。勾选项=代码已闭环；真机项待 98 服实测。

- [x] **凋灵**：侧头（head 1/2）在 `customServerAiStep` 硬编码索敌/乱射，三条开火路径（主头 RangedAttackGoal、侧头锁定射击、侧头 idle 随机乱射）都汇到私有的 5 参 `performRangedAttack(int head,double,..)`；`WitherBossMixin` 在该**开火出口**对 head≥1 且中立化者 cancel（主头 head 0 放行，走保留的 HurtByTargetGoal 反击）。注：初版拦 `setAlternativeTarget` 无法挡住不依赖锁定的 idle 乱射，真机自查时改为开火出口单点拦截
- [x] 凋灵默认**被中立化**（不在默认白名单；既有 scope 配置）
- [x] `boss_trading_enabled=false` 时凋灵中立但不开交易界面（`NeutralizationScope.BOSSES` 含 WITHER，既有）
- [x] 凋灵不再主动发射头颅攻击玩家：主头主动索敌已删（无目标不开火），侧头硬编码已拦；**被玩家攻击后仍会反击**（设计要求，HurtByTargetGoal 保留）
- [x] 凋灵召唤爆炸（invulnerableTicks 分支）/飞行破坏方块是独立代码路径，不经 setAlternativeTarget，保持原版
- [x] **监守者**：振动感知最终要写 ATTACK_TARGET 才会攻击，已由 `BrainAttackGate` 源头门控（非愤怒时拒写攻击记忆）覆盖，无需额外擦 DISTURBANCE 记忆
- [x] 监守者 Sonic Boom 不对中立玩家释放：`SonicBoom` 行为入口要求 `ATTACK_TARGET VALUE_PRESENT`，被门控挡住（0.0.2 已真机验证）
- [x] 监守者默认被中立化（不在默认白名单；既有 scope 配置）
- [x] **两者真机验证**（2026-10-14，98 服 NeoForge + mc-client-rpc）：
  - **凋灵** `verify_neut006_wither.py`：玩家用新增 `placeBlock` 原语亲手放最后一个骷髅头走真实 `checkSpawn` 图案召唤（骑头鸡在出生爆炸中被炸死，爆炸保留）；A 玩家站侧头索敌盒内 24s 全程不掉血、source=NONE（侧头锁定射击 + idle 乱射全被开火出口 Mixin 拦）；B 玩家攻击后 source=PLAYER_DIRECT、主头反击掉血。
  - **监守者** `verify_neut006_warden.py`：铺三层厚板逼其在站立层钻出，用 `sculk_shrieker[can_summon=true]` + 玩家键映射 STEP 直线来回走自然召唤（尖啸体 warning 1→4，非 `/summon`，无 5s 钻地自灭）；A 钻出结束后玩家贴近 0 攻击 8s，HP 20→20、source=NONE/target=none（Sonic Boom/近战被 BrainAttackGate 拦）；B 玩家命中 distance 2.2、HP 500→499、source=PLAYER_DIRECT，监守者近战反击 20→0。本轮对监守者零代码改动，回归确认门控仍生效。

## 技术要点

**凋灵**主头索敌其实是标准 `NearestAttackableTargetGoal`（已随通用策略删除）；真正硬编码的是**两个侧头**在 `WitherBoss#customServerAiStep()` 的索敌与乱射，不经 targetSelector。三条发射路径都汇到私有的 5 参 `performRangedAttack(int head,double,...)`，Mixin 在该开火出口对 head≥1 取消（拦索敌 setter 挡不住不依赖锁定的 idle 乱射）。

**监守者**（2026-10-13 源码实证修正）：振动感知（VibrationSystem）攒的是原版 `anger.suspects`，最终要转成 Brain 的 `ATTACK_TARGET` 记忆才会攻击/放 Sonic Boom；而 ATTACK_TARGET 写入已被 0.0.2 的 `BrainAttackGate#setMemoryInternal` 源头门控（非愤怒拒写）覆盖。无需另擦 DISTURBANCE_LOCATION，本组对监守者零新增代码。

## 产出物（2026-10-13 实际落地）

- 代码：`common/.../mixin/WitherBossMixin.java`（侧头开火出口拦截）；监守者无新代码。
- 注册：`common/src/main/resources/peaceandlove-common.mixins.json`。
- Commit：本分支 `feat/special-mobs-neut-005-007`。

## 备注

凋灵侧头 Mixin 与僵尸猪灵 Mixin 均为运行时行为，纯 JUnit 造不出真实 Boss，未加单测，正确性靠源码核对 + 真机验证（见验收末项）。
