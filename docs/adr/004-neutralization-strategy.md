# ADR-004: 双策略中立化 + 「已适配列表 ∩ 非白名单」生效范围模型

## 状态

Accepted（2026-09-11）
—— 本 ADR 包含两次用户纠正带来的重要修订，见下方"决策演进"

## 背景

需要把敌对生物改造为中立可交易，涉及三个彼此纠缠的问题：

1. **哪些生物**应该被改变行为？
2. 不同生物用**不同的 AI 系统**，如何统一处理？
3. 改变后的**仇恨语义**是什么？

---

## 决策演进（两次纠正）

### 纠正一：白名单 ≠ 零工作量

**原判断**（v2）：默认白名单内的 6 种生物（掠夺者/卫道士/唤魔者/恼鬼/幻翼/潜影贝）与 2 个 Boss「天然跳过，工作量为零」。

**用户指出**：白名单是**运行时配置**，管理员可以把任何生物移出白名单。移出后代码必须能正确工作，否则就是 bug。

**结论**：白名单是"要不要做"的策略，不是"能不能做"的能力边界。**全部生物都必须适配**。

### 纠正二：末影龙实为第三类 AI

修正分类时用「是否覆写 `makeBrain()`」做二分判定，漏掉了第三种可能。字节码复核发现：

| 生物 | 实测结果 | 先前说法 |
|------|---------|---------|
| **凋灵** | ✅ 引用 `goalSelector`/`targetSelector`，覆写 `registerGoals()` → **标准 Goal 系** | ❌ 曾说"Boss 专属弹幕 AI，标准改写不适用" |
| **末影龙** | ❌ 完全不引用 goal/target selector，使用 `EnderDragonPhaseManager` → **自有 AI** | ❌ 曾说"与凋灵同类" |

### 纠正三：仇恨语义大幅收窄

**原设计**：通用仇恨系统 —— 任何伤害都触发状态切换与同族示警。

**用户澄清**：模组新增的仇恨/示警机制**仅在受到玩家攻击时生效**，仇恨**锁定攻击者本人**，不扩散到其他玩家、不扩散到 NPC；NPC 攻击时**只走原版既有机制**，模组不介入。

---

## 决策一：生效范围 = 已适配列表 ∩ 非白名单

```
某生物是否被中立化 = (在 AdaptedMobRegistry 中) AND (不在 hostile_whitelist 中)
```

| 概念 | 性质 | 可变性 |
|------|------|--------|
| **已适配生物列表** | 代码的**能力边界** | 只读常量，随版本更新 |
| **白名单** | 管理员的**策略选择** | 运行时可配置，可增可减 |

### v1.0 已适配列表：38 个

| 分类 | 数量 | 说明 |
|------|------|------|
| Goal 系 | 32 | 覆写 `registerGoals()` + 引用 `goalSelector`/`targetSelector` |
| Brain 系 | 6 | 猪灵、猪灵蛮兵、疣猪兽、僵尸疣猪兽、监守者、旋风人 |
| ~~自有 AI~~ | ~~1~~ | 末影龙 —— **v1.0 暂缓，不进已适配列表** |

### 默认白名单：6 个

掠夺者、卫道士、唤魔者、恼鬼、幻翼、潜影贝 —— **均已适配**，管理员移出白名单后立即生效。

### 凋灵：已适配，不在默认白名单（用户 2026-09-11 决策）

凋灵经字节码复核确认为**标准 Goal 系**，先前"Boss 专属弹幕 AI"是误判。归类修正后曾一度归入默认白名单，用户裁定**移出** —— 与监守者同等对待，默认被中立化。

`boss_trading_enabled` 默认 `false`，因此凋灵默认「中立化但不开交易」：不主动攻击玩家，被攻击仍会反击。管理员若要恢复原版凋灵战，把 `minecraft:wither` 加入白名单即可。

### 监守者：已适配且不在默认白名单

即默认被中立化并可交易。

### 末影龙：不适配 + 不进白名单

管理员无论怎么配置都不会改变其行为，日志给 INFO 级提示说明原因。

---

## 决策二：双策略抽象

```java
interface NeutralizationStrategy {
    boolean supports(EntityType<?> type);
    void neutralize(Mob mob);
    void restore(Mob mob);      // 白名单热重载时恢复原版行为
}
```

| 实现 | 覆盖 | 手段 |
|------|------|------|
| `GoalBasedStrategy` | 32 个 | `goalSelector.removeAllGoals(Predicate)` 移除主动索敌，保留 `HurtByTargetGoal` |
| `BrainBasedStrategy` | 6 个 | 擦除 `ANGRY_AT` / `ATTACK_TARGET` 记忆 + 拦截索敌 Behavior |
| ~~`CustomAiStrategy`~~ | 末影龙 | v1.1 |

### 实测依据：`GoalSelector` 有 `removeAllGoals(Predicate)`

```java
void              addGoal(int, Goal);
void              removeAllGoals(Predicate<Goal>);   // ★ 按谓词批量移除
void              removeAllGoals(Goal);
Set<WrappedGoal>  getAvailableGoals();               // 可遍历检查
```

`WrappedGoal.getGoal()` / `getPriority()` 均为 public —— 移除前记录 `(priority, goal)` 对即可在 `restore()` 中原样重建，**满足白名单热重载的可逆性要求，且无需反射**。

### 8 个需特殊适配的生物

| 生物 | 难点 |
|------|------|
| 潜影贝 | 固定在方块上，索敌内嵌于 `ShulkerAttackGoal`，无独立移动 Goal |
| 幻翼 | `PhantomAttackPlayerTargetGoal`；另有"玩家不睡觉才生成"的生成条件 |
| 掠夺者 / 卫道士 / 唤魔者 | 袭击系统，需处理 `Raider.canJoinRaid`；卫道士有 Johnny 名牌；唤魔者需管理召唤物 |
| 恼鬼 | 有 owner 概念，生命周期绑定唤魔者 |
| 凋灵 | target 选择在 `customServerAiStep` 中另有硬编码 |
| 监守者 | `VibrationSystem` + `AngerManagement`，震动感知机制独立于常规索敌 |

---

## 决策三：仇恨语义 —— 仅玩家攻击触发，仇恨单目标

### 触发矩阵

| 伤害来源 | 模组是否介入 |
|---------|-------------|
| 玩家直接攻击 | ✅ **唯一触发条件** |
| 玩家投射物 / TNT / 宠物 | ✅ owner 是玩家则视同（`DamageSource.getEntity()` 已自动解析） |
| 铁傀儡、村民卫兵、其他怪物 | ❌ **完全不介入**，走原版逻辑 |
| 环境伤害（跌落、岩浆、窒息） | ❌ 不介入 |

### 注入点：`LivingEntity.hurt(DamageSource, float)`

```java
Entity attacker = source.getEntity();          // 逻辑攻击者（射箭的玩家）
if (attacker instanceof Player player) {
    // 仅此路径触发中立 → 敌对
}
```

### 状态存储：复用原版 `NeutralMob`

```java
UUID  getPersistentAngerTarget();     // ★ 单目标 UUID —— 与需求语义天然吻合
int   getRemainingPersistentAngerTime();
void  startPersistentAngerTimer();
void  stopBeingAngry();
void  addPersistentAngerSaveData(CompoundTag);   // NBT 持久化免费
```

### 同族示警：单层，不链式

- 范围：球形 4.0 格（可配置）
- 条件：**严格同一 `EntityType`**
- 被示警的个体标记 `angerSource = KIN_ALERT`，**不再向外示警**
- 脱战 30 秒（可配置）恢复中立，可再次交易

---

## 后果

### 正面

- **「已适配 ∩ 非白名单」模型一次解决三个问题**：
  1. 第三方 Mod 生物不在已适配列表 → **天然不受影响**，`../RISKS.md` R6 直接关闭，连 `neutralize_modded_mobs` 开关都不需要
  2. 末影龙语义一致 —— 不用尴尬地"放进白名单假装支持"
  3. 能力与策略分离，边界清晰
- 仇恨语义收窄后，**R7（示警链失控）从 M 降到 L** —— 触发路径从"任意伤害源"收窄到单一路径，且仇恨单目标，雪崩式全场敌对几乎不可能
- **R5 苦力怕问题自然消解** —— 爆炸不是玩家攻击，被波及的中立怪物不会转敌对，语义自洽
- **R5 蠹虫不再是冲突** —— 模组只管状态切换，敌对后的原版群体唤醒是正常行为，不干预不叠加
- 复用 `NeutralMob` 使冷却计时与 NBT 持久化零成本
- `removeAllGoals(Predicate)` 存在意味着无需反射操作内部集合

### 负面

- 工作量从"31 个"增加到"38 个"（+23%），其中 8 个需要单独适配
- ⚠️ ~~猪灵 / 猪灵蛮兵 / 疣猪兽 / 僵尸疣猪兽**原本就实现** `NeutralMob`~~ —— **该描述有误，已由 P4 验证推翻**。
  实际情况：这 4 个 Brain 系生物**都没有**实现 `NeutralMob`。真正实现的是 **末影人**与**僵尸猪灵**（均为 Goal 系）。详见下方"P4 验证结果"。
- ⚠️ **禁止调用 `forgetCurrentTargetAndRefreshUniversalAnger()`** —— 它有"对所有玩家记仇"（universal anger）语义，会违反"不扩散到其他玩家"的要求
- 需为每个已适配生物维护 `(priority, goal)` 快照以支持 `restore()`，增加内存占用（可接受，每实体几十字节）
- 已适配列表需随 MC 版本更新人工核对

### 中性

- 玩家可能困惑于"为什么这个 Mod 生物没变化" —— 通过日志与文档说明缓解
- 未来可提供 API 让第三方 Mod 主动注册进已适配列表（opt-in，P2 需求）

---

## 备选方案

### 生效范围模型

**纯排除清单（原设计）**：默认中立化所有敌对生物，白名单排除
- 缺点：波及所有第三方 Mod 生物，它们的自定义 Boss 可能被中立化并算出荒谬价格
- 不选的原因：用户明确要求改为双重决策模型

**纯包含清单（无白名单）**：只中立化已适配列表，不提供白名单
- 缺点：管理员无法保留特定生物的原版行为（如保护袭击玩法）
- 不选的原因：违反 FR-1.5

### 中立化手段

**Mixin `Mob.canAttack` 统一拦截**
- 优点：一套代码覆盖 Goal 与 Brain 两系；天然可逆
- 缺点：可能误伤正当反击；对已进入攻击状态的生物行为不确定；无法精确区分"主动索敌"与"受击反击"
- 不选的原因：精确度不足。但**作为 Brain 系的辅助手段保留**

**改写 `targetSelector` 全局拦截**
- 缺点：与原版兼容性差；难以区分不同 Goal 的语义
- 不选的原因：过于粗暴

---

## 待验证

| # | 验证项 | 状态 |
|---|--------|------|
| **P4** | 原版已实现 `NeutralMob` 的生物是否与本模组冲突 | ✅ **已完成** —— 见下方 |

---

## P4 验证结果（2026-09-11）

**验证脚本**：`spikes/design-verify/verify_p4_v3.py`（全 jar 扫描 + 继承链递归）

### 原假设被推翻

原 ADR 称"猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽 4 个 Brain 系生物已实现 `NeutralMob`"。字节码实测：

| 生物 | 直接接口 | 父类 | 实现 `NeutralMob`？ |
|------|---------|------|-------------------|
| 猪灵 | `CrossbowAttackMob`, `InventoryCarrier` | `AbstractPiglin` | ❌ **否** |
| 猪灵蛮兵 | （无） | `AbstractPiglin` | ❌ **否** |
| 疣猪兽 | `Enemy`, `HoglinBase` | `Animal` | ❌ **否** |
| 僵尸疣猪兽 | `Enemy`, `HoglinBase` | `Monster` | ❌ **否** |
| 监守者 | `VibrationSystem` | `Monster` | ❌ **否** |
| 旋风人 | （无） | `Monster` | ❌ **否** |

沿继承链递归查找（`AbstractPiglin` → `Monster` → …）同样未找到 `NeutralMob`。

### 全量扫描：原版共 6 个类实现 `NeutralMob`

```
net.minecraft.world.entity.animal.Bee              蜜蜂
net.minecraft.world.entity.animal.IronGolem        铁傀儡
net.minecraft.world.entity.animal.PolarBear        北极熊
net.minecraft.world.entity.animal.Wolf             狼
net.minecraft.world.entity.monster.EnderMan        末影人        ★ 在适配列表
net.minecraft.world.entity.monster.ZombifiedPiglin 僵尸猪灵      ★ 在适配列表
```

### 真正的交集：2 个，且都是 Goal 系

| 生物 | AI 系统 | 覆写的 `NeutralMob` 方法 | 自有 anger 字段 | 引用危险方法 |
|------|---------|------------------------|----------------|-------------|
| **末影人** | Goal | 5 个（`get/setPersistentAngerTarget`、`get/setRemainingPersistentAngerTime`、`startPersistentAngerTimer`） | 无 | ✅ 否 |
| **僵尸猪灵** | Goal | 同上 5 个 | 无 | ✅ 否 |

**两个都没有引用 `forgetCurrentTargetAndRefreshUniversalAnger()`** —— 本模组「仇恨不扩散到其他玩家」的约束不会被原版代码破坏。

### 结论：无冲突，但有 2 个实现注意点

1. **末影人**：`setTarget()` 与 `hurt()` 均被覆写，且有 `isLookingAtMe(Player)` / `setBeingStaredAt()` 的"凝视激怒"专属机制。
   本模组的中立化需**额外禁用凝视激怒**（它是一种主动索敌，不属于"受玩家攻击"）。
   → 归入特殊适配，`EndermanAdapter`。**特殊适配数从 8 增至 9。**

2. **僵尸猪灵**：`customServerAiStep()` 被覆写，内含群体报复逻辑（一只被激怒会传染给周围同类）。
   这与本模组的「同族示警 4 格单层」机制**功能重叠**。
   → 需在 `neutralize()` 中禁用原版群体报复，改由 `KinAlerter` 统一接管，避免双份逻辑导致范围失控。
   → 归入特殊适配，`ZombifiedPiglinAdapter`。**特殊适配数增至 10。**

3. 这 2 个生物已实现的 5 个 `NeutralMob` 方法**可直接复用**，本模组无需为它们重复实现存储层。

---

## 参考资料

- AI 系统分类：`spikes/r3-ai/classify_v3.py` → `neutralization_plan_v3.json`
- Boss AI 复核：`spikes/r3-ai/verify_boss_ai.py`
- API 签名实测：`spikes/design-verify/verify_critical_v2.py`
- 风险登记：`../RISKS.md` R3 / R5 / R6 / R7 / R9
