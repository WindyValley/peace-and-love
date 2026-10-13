# Peace And Love — 技术选型对比

- 版本：v1.0
- 日期：2026-09-11
- 依据：`01-requirements.md` v0.3、`SPIKE-REPORT.md` v1.1
- 原则：**所有 MC 内部 API 签名均来自 1.21.1 官方 server.jar + 官方 mappings 实测**，无一处凭印象

---

## 决策 1：多加载器方案

| 维度 | A. Architectury | B. 两套独立源码 | C. 仅 Fabric |
|------|----------------|----------------|-------------|
| 代码复用率 | ~85%（common 模块） | 0% | —— |
| 构建复杂度 | 中（Loom + 三 module） | 低 | 最低 |
| Mixin 可移植性 | common 内 Mixin 双端通用 | 需写两遍 | —— |
| 版本迭代成本 | 单点修改 | ×2 | ×1 |
| 社区成熟度 | 高（大量主流 Mod 采用） | —— | —— |
| 覆盖用户 | Fabric + NeoForge | 同 A | 约半数 |

**决策：A（Architectury）**

**代价：**
- 引入 Architectury API 运行时依赖，玩家需额外安装
- 构建产物三份（common 不发布），CI 时间约 ×2
- 平台专属 API 需走 `@ExpectPlatform` 或 service loader，有一层间接

**回退路径：** 若 Architectury 对 1.21.x 支持滞后，退到 B（两套源码），common 逻辑已隔离，迁移成本可控。

**已核实版本**（2026-09-11）：Architectury Loom `1.11.454`、Architectury API `13.0.11`、Fabric API `0.116.17+1.21.1`、NeoForge `21.1.250`

---

## 决策 2：交易能力注入方式

> ⚠️ 此项在 spike 中**推翻了初始判断**。原推荐方案 B，实测后改为 A。

| 维度 | A. Mixin 注入 `Merchant` | B. 自建 Menu + 网络包 | C. 生成隐形村民 |
|------|------------------------|---------------------|---------------|
| 需实现方法数 | **9 个**（实测） | 20+ | —— |
| 字段依赖 | **0**（纯行为接口） | —— | —— |
| GUI | **复用原版 `MerchantMenu`** | 自写 Screen + 贴图 | 复用 |
| 网络同步 | **原版 `sendMerchantOffers` 已有** | 自定义 packet ×3 | 原版 |
| 交易次数机制 | **`MerchantOffer` 已含 uses/maxUses** | 自写 | 已有 |
| 客户端是否必装 | **不需要**（P2 已真机验证 2026-10-12：零 PAL 类客户端连 PAL 服务端照常交易，见 `P1-P4-VERIFY.md` §P2） | 必装 | 不需要 |
| 实体生命周期 | 无额外负担 | 无 | 需同步位置/存活/移除 |
| **总工作量** | **最低** ✅ | 高 | 中（但坑多） |

**决策：A（Mixin 注入 `Merchant` 接口）**

**实测依据**（1.21.1 `net.minecraft.world.item.trading.Merchant`）：

```java
// 全部 9 个方法，无一个依赖字段
void            setTradingPlayer(Player)      // abstract
Player          getTradingPlayer()            // abstract
MerchantOffers  getOffers()                   // abstract
void            notifyTradeUpdated(ItemStack) // abstract
int             getVillagerXp()               // abstract
boolean         showProgressBar()             // abstract  → return false
SoundEvent      getNotifyTradeSound()         // abstract
boolean         isClientSide()                // abstract
boolean         canRestock()                  // ★ 已有 default 实现
```

**代价：**
- Mixin 注入接口，与其他修改 `Mob` 的 Mod 有潜在冲突（R10）
- NeoForge 侧可能需要 Access Transformer（P1 待验证）
- 若注入 `Mob` 基类，影响面覆盖所有生物（需运行时判定拦截）

**回退路径：** 若 NeoForge 接口注入受阻，改为 38 个目标类逐一注入（代码量增加但机制不变）。

---

## 决策 3：交易次数与补货机制

| 维度 | A. 复用 `MerchantOffer` | B. 自建 `Map<ItemId, day>` |
|------|------------------------|---------------------------|
| 需新增字段 | **1 个**（`lastRestockDay`） | Map + 序列化 |
| NBT 持久化 | 原版 CODEC 已覆盖 offers | 需自写 |
| 客户端显示"售罄" | **原版自动**（`isOutOfStock`） | 需自己同步 |
| 语义匹配度 | `maxUses=1` + 每日补货 ≡ 需求 | 等价但绕远 |

**决策：A**

**实测依据**（`MerchantOffer` 字段）：

```java
private       int     uses;              // ★ 已用次数
private final int     maxUses;           // ★ 次数上限
private       int     demand;
private final float   priceMultiplier;
// 方法：resetUses() increaseUses() isOutOfStock() setToOutOfStock()
```

```
maxUses = 1  +  每游戏日补货一次  ≡  「每天最多买到一次击杀的量」
```

**代价：**
- ⚠️ **不能直接调用 `Villager.restock()`** —— 它耦合 gossip/demand/价格波动，需自写精简版 `resetAllUses()`
- `MerchantOffer` 的 `demand`/`priceMultiplier` 会让原版村民出现价格波动，本模组需固定为 `priceMultiplier=0` 以禁用

---

## 决策 4：中立化实现策略

| 维度 | A. 移除索敌 Goal | B. Mixin `canAttack` | C. 改 `targetSelector` 全局拦截 |
|------|-----------------|---------------------|------------------------------|
| 精确度 | 高（只动索敌） | 中（可能误伤反击） | 低 |
| 对 Brain 系有效 | ❌ 否，需另写 | ✅ 是 | ❌ |
| 可逆性 | 需重建 Goal | 天然可逆 | 天然可逆 |
| 与原版兼容 | 好 | 中 | 差 |

**决策：A + B 混合**
- **Goal 系（32 个）**：`goalSelector.removeAllGoals(Predicate)` 移除主动索敌 Goal，保留 `HurtByTargetGoal`
- **Brain 系（6 个）**：擦除 `ANGRY_AT` / `ATTACK_TARGET` 记忆 + 拦截索敌 Behavior

**实测依据**（`GoalSelector` 完整 API）：

```java
void  addGoal(int, Goal)
void  removeAllGoals(Predicate<Goal>)   // ★ 关键：按谓词批量移除
void  removeAllGoals(Goal)
Set<WrappedGoal>  getAvailableGoals()   // 可遍历检查
void  tick()
```

> ✅ **`removeAllGoals(Predicate)` 存在**，无需反射操作内部集合。
> `getAvailableGoals()` 返回 `Set<WrappedGoal>`，`WrappedGoal.getGoal()` 取原始 Goal，
> `WrappedGoal.getPriority()` 取优先级 —— 移除后可原样重建，满足「可逆」要求。

**代价：**
- 移除 Goal 后若要恢复（白名单热重载），需记录原始 `(priority, goal)` 对
- Brain 系需要为 6 个生物单独适配，无法一套代码覆盖

---

## 决策 5：仇恨状态存储

| 维度 | A. 复用 `NeutralMob` | B. 自建 NBT 字段 |
|------|---------------------|-----------------|
| 冷却计时 | **原版已有** | 自写 tick |
| 目标持久化 | **原版 UUID 字段** | 自写 |
| 与猪灵/疣猪兽冲突 | ⚠️ 需检查（它们已实现） | 无冲突但重复 |
| 语义匹配 | **单目标 UUID，天然吻合** | 等价 |

**决策：A（复用 `NeutralMob`）**

**实测依据**：

```java
// net.minecraft.world.entity.NeutralMob
int      getRemainingPersistentAngerTime();  // abstract
UUID     getPersistentAngerTarget();         // abstract ★ 单目标 UUID
void     startPersistentAngerTimer();        // abstract
boolean  isAngry();                          // default
void     stopBeingAngry();                   // default
void     forgetCurrentTargetAndRefreshUniversalAnger();  // default
void     addPersistentAngerSaveData(CompoundTag);        // default ★ NBT 已覆盖
```

> 📌 `getPersistentAngerTarget()` 返回**单个 UUID** —— 与「仇恨只锁定攻击者玩家、
> 不扩散到其他玩家或 NPC」的需求语义完全一致。

**代价：**
- ⚠️ 猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽**原本就实现** `NeutralMob`，需检查与原版逻辑（尤其猪灵"穿金装中立"和群体报复）是否冲突
- `forgetCurrentTargetAndRefreshUniversalAnger()` 有"universal anger"语义（对所有玩家记仇），**本模组必须避免调用**，否则违反"不扩散到其他玩家"

---

## 决策 6：仇恨触发点注入位置

| 维度 | A. `LivingEntity.hurt` | B. `Mob.setTarget` | C. Fabric/NeoForge 事件 API |
|------|----------------------|-------------------|---------------------------|
| 能拿到 `DamageSource` | ✅ | ❌ | ✅ |
| 双端统一 | ✅（common Mixin） | ✅ | ❌ 两套 API |
| 时机准确 | ✅ 伤害生效时 | 滞后 | 依平台而定 |

**决策：A（Mixin `LivingEntity.hurt`）**

**实测依据**：

```java
// net.minecraft.world.entity.LivingEntity  （混淆名 a）
boolean hurt(DamageSource, float)

// net.minecraft.world.damagesource.DamageSource
Entity  getEntity()        // ★ 逻辑攻击者（射箭的玩家）
Entity  getDirectEntity()  // 直接实体（箭矢本身）
boolean isDirect()
```

判定「是否玩家攻击」：

```java
Entity attacker = source.getEntity();   // 已自动解析投射物 owner
if (attacker instanceof Player player) { /* 触发中立→敌对 */ }
```

**代价：** `hurt` 是高频调用点，Mixin 需尽早返回以降低开销（先查是否在已适配列表）。

---

## 决策 7：定价算法曲线

| 维度 | A. 对数曲线 | B. 线性反比 `k/epk` | C. 分段查表 |
|------|-----------|-------------------|-----------|
| 稀有区间分辨率 | **好** | ❌ 7/23 撞上限 | 好 |
| 可配置性 | 2 个锚点 | 1 个系数 | 需维护表 |
| 单调性 | **110/110 通过** | 通过 | 人工保证 |
| 新增生物自适应 | ✅ | ✅ | ❌ 需手工加 |

**决策：A（对数曲线）**

```
pos   = log(cheap / epk) / log(cheap / rare)     // 归一化到 [0,1]
price = clamp(1 + (PRICE_MAX - 1) × pos, 1, PRICE_MAX)

默认：cheap = 2.0，rare = 0.005，PRICE_MAX = 128
```

**性质**：产出每减半，价格稳定增加约 `(PRICE_MAX-1)/log2(cheap/rare) ≈ 14.7` 绿宝石（等比稀有度 → 等量价格）。

**代价：** 锚点外的极端值会被 clamp，超稀有物品之间不再区分（可用 `price_overrides` 手工修正）。

---

## 决策 8：战利品表读取方式

| 维度 | A. record accessor + 7 个 Mixin Accessor | B. 全反射 | C. 硬编码价格表 |
|------|----------------------------------------|----------|---------------|
| Mixin 面积 | **7 个 `@Accessor`** | 0 | 0 |
| 版本适配成本 | 低 | 中（字段名易变） | 高（每版手工核对） |
| 支持数据包自定义表 | ✅ | ✅ | ❌ |
| 运行时开销 | 一次性（启动扫描） | 反射较慢 | 无 |

**决策：A**

**实测依据**：`LootTable` 在 1.21.1 是 **record**，`pools()` 有 public accessor，结构遍历零 Mixin。仅 7 个内部字段需 `@Accessor`。

**代价：** 7 个 Accessor 随版本可能失效，需在 `LootPriceProvider` 接口后隔离（为 1.21.8/1.21.11 留位）。

---

## 汇总

| # | 决策点 | 结论 | 风险 |
|---|--------|------|------|
| 1 | 多加载器 | Architectury | 🟢 L |
| 2 | 交易注入 | Mixin `Merchant` 接口（方案 A） | 🟡 M（P1 待验证） |
| 3 | 交易次数 | `MerchantOffer.maxUses=1` + 每日补货 | 🟢 L |
| 4 | 中立化 | Goal 移除 + Brain 记忆擦除 | 🟡 M |
| 5 | 仇恨存储 | 复用 `NeutralMob` | 🟢 L（猪灵需检查） |
| 6 | 触发点 | Mixin `LivingEntity.hurt` | 🟢 L |
| 7 | 定价曲线 | 对数，双锚点可配 | 🟢 L |
| 8 | 战利品表 | record accessor + 7 Mixin | 🟢 L |

## 建议做 spike 验证的选项

| # | 验证项 | 关联决策 | 原因 |
|---|--------|---------|------|
| **P1** | NeoForge Mixin 接口注入是否需要 Access Transformer | 决策 2 | 方案 A 唯一残留不确定性 |
| **P2** | 客户端不装模组能否交易 | 决策 2 | 若能则是重要卖点 |
| **P3** | 注入 `Mob` 基类 vs 38 个目标类 | 决策 2 | 影响面 vs 代码量权衡 |
| **P4** | 猪灵/疣猪兽的 `NeutralMob` 是否冲突 | 决策 5 | 4 个生物已实现该接口 |

---

## 变更记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-09-11 | v1.0 | 首版，8 项决策，全部 API 签名经 1.21.1 字节码实测 |
