# Peace And Love — 架构图

- 版本：v1.0
- 日期：2026-09-11
- 绘图规范：**优先 Mermaid**，仅在 Mermaid 表达受限处降级 ASCII

---

## 1. Context 图（C4 Level 1）

```mermaid
graph LR
    Player["🧑 玩家<br/>种田/建筑党"]
    Admin["🛠 服务器管理员"]
    Mod["📦 Peace And Love<br/>peaceandlove"]
    MC["🎮 Minecraft 1.21.1<br/>Fabric / NeoForge"]
    Datapack["📄 数据包<br/>战利品表"]

    Player -->|"右键交易 / 攻击怪物"| Mod
    Admin -->|"编辑 config"| Mod
    Mod -->|"Mixin 注入"| MC
    Mod -->|"启动时扫描"| Datapack
    MC -->|"实体/伤害/GUI 事件"| Mod
```

---

## 2. Container 图（C4 Level 2）

```mermaid
graph TB
    subgraph common["common 模块（Architectury，~85% 代码）"]
        direction TB
        Config["ConfigManager<br/>配置加载与热重载"]
        Registry["AdaptedMobRegistry<br/>已适配生物列表（代码常量）"]
        Scope["NeutralizationScope<br/>生效判定：适配 ∩ !白名单"]
        Pricing["PricingEngine<br/>对数曲线定价"]
        Loot["LootPriceProvider<br/>战利品表解析（接口）"]
        Strategy["NeutralizationStrategy<br/>中立化策略（接口）"]
        Trade["TradeOfferBuilder<br/>生成 MerchantOffers"]
        Restock["RestockManager<br/>每日补货"]
        Anger["AngerController<br/>仇恨状态切换 + 同族示警"]
    end

    subgraph mixin["common Mixin"]
        MxMob["MobMixin<br/>implements Merchant"]
        MxHurt["LivingEntityHurtMixin<br/>仇恨触发点"]
        MxLoot["LootTableAccessor ×7<br/>@Accessor"]
    end

    subgraph fabric["fabric 模块"]
        FabInit["FabricInitializer"]
        FabCfg["Fabric 配置桥接"]
    end

    subgraph neoforge["neoforge 模块"]
        NeoInit["NeoForgeInitializer"]
        NeoCfg["NeoForge 配置桥接"]
        NeoAT["accesstransformer.cfg<br/>（P1 待验证是否需要）"]
    end

    subgraph vanilla["Minecraft 原版"]
        VMob["Mob / LivingEntity"]
        VMenu["MerchantMenu<br/>（复用，不自建）"]
        VOffer["MerchantOffer<br/>uses / maxUses"]
        VNeutral["NeutralMob<br/>记仇与冷却"]
        VLoot["LootTable（record）"]
    end

    FabInit --> Config
    NeoInit --> Config
    Config --> Scope
    Registry --> Scope
    Scope --> Strategy
    Scope --> Trade
    Loot --> Pricing
    Pricing --> Trade
    Trade --> Restock
    Trade -.生成.-> VOffer
    MxMob -.实现.-> VMenu
    MxHurt --> Anger
    Anger --> Strategy
    Anger -.复用.-> VNeutral
    MxLoot -.读取.-> VLoot
    Strategy -.操作.-> VMob
    MxMob -.注入.-> VMob
```

---

## 3. Component 图 —— 中立化策略

```mermaid
graph TB
    IFace["«interface»<br/>NeutralizationStrategy"]

    Goal["GoalBasedStrategy<br/>32 个生物"]
    Brain["BrainBasedStrategy<br/>6 个生物"]
    Custom["⏸ CustomAiStrategy<br/>末影龙 · v1.1"]

    IFace --> Goal
    IFace --> Brain
    IFace -.暂缓.-> Custom

    subgraph goalimpl["Goal 系实现"]
        G1["removeAllGoals(Predicate)<br/>移除主动索敌"]
        G2["保留 HurtByTargetGoal"]
        G3["记录 (priority, goal)<br/>供白名单热重载恢复"]
    end

    subgraph brainimpl["Brain 系实现"]
        B1["eraseMemory(ANGRY_AT)"]
        B2["eraseMemory(ATTACK_TARGET)"]
        B3["拦截索敌 Behavior"]
    end

    subgraph special["特殊适配（源码实证后仅 3 个真缺口）"]
        S2["幻翼：裸 Goal 索敌器<br/>谓词收窄为「targetSelector 除 HurtBy 外全删」"]
        S5["凋灵侧头：customServerAiStep 硬编码<br/>WitherBossMixin 拦 setAlternativeTarget(head≥1)"]
        S7["僵尸猪灵：customServerAiStep 私有 alertOthers<br/>ZombifiedPiglinMixin 拦 35 格大范围传染"]
    end

    subgraph covered["源码实证已被通用策略覆盖（无额外代码）"]
        C1["潜影贝/Johnny/袭击系×3/恼鬼：索敌均为 TargetGoal 子类，已删<br/>袭击寻路 goal 在 goalSelector 保留；唤魔者无目标不召唤"]
        C2["末影人凝视：EndermanLookForPlayerGoal 已删；瞬移/搬方块保留"]
        C3["监守者 Sonic Boom：ATTACK_TARGET 被 BrainAttackGate 源头拦截"]
    end

    Goal --> goalimpl
    Brain --> brainimpl
    goalimpl -.仅 3 处需额外处理.-> special
    goalimpl -.7 项已覆盖.-> covered
    brainimpl -.已覆盖.-> covered
```

---

## 4. 生效范围判定（决策核心）

```mermaid
flowchart TB
    Start(["生物 E 生成 / 加载"]) --> Q1{"E 在<br/>AdaptedMobRegistry<br/>已适配列表？"}
    Q1 -->|"❌ 否<br/>（第三方 Mod 生物、末影龙）"| Vanilla["保持原版行为<br/>模组完全不介入"]
    Q1 -->|"✅ 是"| Q2{"E 在<br/>hostile_whitelist<br/>白名单？"}
    Q2 -->|"✅ 是<br/>（默认 6 项）"| Vanilla
    Q2 -->|"❌ 否"| Neutral["应用中立化<br/>+ 生成交易 offer"]

    Neutral --> Q3{"E 是 Boss？<br/>（凋灵）"}
    Q3 -->|"是"| Q4{"boss_trading_enabled?"}
    Q4 -->|"false（默认）"| OnlyNeutral["仅中立化<br/>不生成 offer"]
    Q4 -->|"true"| Full["中立化 + 交易"]
    Q3 -->|"否"| Full

    style Vanilla fill:#3a3a3a,color:#fff
    style Full fill:#2d5016,color:#fff
    style OnlyNeutral fill:#5c4317,color:#fff
```

---

## 5. 时序图 —— 场景 1：玩家与中立僵尸交易

```mermaid
sequenceDiagram
    actor P as 玩家
    participant Z as 僵尸<br/>(MobMixin: Merchant)
    participant S as NeutralizationScope
    participant T as TradeOfferBuilder
    participant R as RestockManager
    participant M as MerchantMenu<br/>(原版)

    P->>Z: 右键点击
    Z->>S: isNeutralized(zombie)?
    S-->>Z: true（已适配 ∩ 非白名单）
    Z->>Z: getOffers()
    alt 首次交互
        Z->>T: buildOffers(EntityType.ZOMBIE)
        T->>T: 读缓存的定价结果
        T-->>Z: MerchantOffers<br/>[腐肉×2=16绿, 铁锭×1=117绿, ...]
    else 已有 offers
        Z->>R: shouldRestock(lastRestockDay)?
        alt 已过补货周期
            R->>Z: resetAllUses()<br/>（自写，非 Villager.restock）
            R->>Z: lastRestockDay = currentDay
        end
    end
    Z->>Z: setTradingPlayer(player)
    Z->>M: openMenu(MerchantMenu)
    M-->>P: 显示交易界面
    P->>M: 选择「8 绿宝石 → 2 腐肉」
    M->>Z: notifyTradeUpdated(result)
    Z->>Z: offer.increaseUses()<br/>uses=1 == maxUses=1
    Z-->>M: isOutOfStock() = true
    M-->>P: 该条目显示为售罄（原版行为）
```

---

## 6. 时序图 —— 场景 2：玩家攻击触发仇恨 + 同族示警

> ★ 核心语义：**仅玩家攻击触发**，仇恨**只锁定该玩家**，**单层不链式**

```mermaid
sequenceDiagram
    actor P as 玩家 A
    participant Z1 as 僵尸 Z1<br/>(被攻击)
    participant H as LivingEntityHurtMixin
    participant AC as AngerController
    participant Z2 as 僵尸 Z2<br/>(4格内)
    participant Z3 as 僵尸 Z3<br/>(6格外)
    participant IG as 铁傀儡

    P->>Z1: 攻击
    Z1->>H: hurt(DamageSource, amount)
    H->>H: source.getEntity() instanceof Player?
    H-->>AC: ✅ 是玩家 → onPlayerAttack(Z1, A)

    AC->>Z1: setTarget(A)
    AC->>Z1: setPersistentAngerTarget(A.uuid)
    AC->>Z1: startPersistentAngerTimer()
    AC->>Z1: angerSource = PLAYER_DIRECT

    AC->>AC: alertKin(Z1, radius=4.0)<br/>严格同 EntityType
    AC->>Z2: setTarget(A) + angerSource = KIN_ALERT
    Note over Z2: ❌ 不再触发自己的 alertKin()<br/>（单层，禁止链式）
    Note over Z3: ✅ 6 格外，保持中立

    Note over IG,Z1: —— 对照：NPC 攻击 ——
    IG->>Z1: 攻击
    Z1->>H: hurt(DamageSource, amount)
    H->>H: source.getEntity() instanceof Player?
    H-->>H: ❌ 否 → 直接放行，不介入
    Note over Z1: 走原版逻辑<br/>不切状态、不示警、不标记
```

---

## 7. 时序图 —— 场景 3：仇恨冷却回归中立

```mermaid
sequenceDiagram
    actor P as 玩家 A
    participant Z as 僵尸（敌对中）
    participant AC as AngerController
    participant NM as NeutralMob<br/>(原版机制)

    Note over Z: 已敌对，target = A
    P->>P: 逃离至 32 格外
    loop 每 tick
        Z->>NM: remainingPersistentAngerTime--
    end
    Note over Z: 30 秒（默认，可配）
    NM-->>AC: isAngry() = false
    AC->>Z: stopBeingAngry()
    AC->>Z: setTarget(null)
    AC->>Z: angerSource = NONE
    Note over Z: ✅ 恢复中立，可再次交易

    Note over AC,NM: ⚠️ 禁止调用<br/>forgetCurrentTargetAndRefreshUniversalAnger()<br/>它有"对所有玩家记仇"语义<br/>违反「不扩散到其他玩家」
```

---

## 8. 状态机 —— 生物的中立/敌对状态

```mermaid
stateDiagram-v2
    [*] --> Neutral: 生成（在适配范围内）

    Neutral --> Hostile_Direct: 玩家直接攻击
    Neutral --> Hostile_Alerted: 4格内同族被玩家攻击
    Neutral --> Neutral: NPC攻击 / 环境伤害<br/>（模组不介入）

    Hostile_Direct --> Neutral: 冷却 30s 未受伤
    Hostile_Alerted --> Neutral: 冷却 30s 未受伤

    Hostile_Direct --> Hostile_Direct: 再次受玩家伤害<br/>（冷却重置）
    Hostile_Alerted --> Hostile_Direct: 被该玩家直接攻击

    state Neutral {
        [*] --> CanTrade
        CanTrade: ✅ 可交易<br/>angerSource = NONE
    }
    state Hostile_Direct {
        [*] --> Chasing1
        Chasing1: ❌ 不可交易<br/>angerSource = PLAYER_DIRECT<br/>target = 攻击者玩家
    }
    state Hostile_Alerted {
        [*] --> Chasing2
        Chasing2: ❌ 不可交易<br/>angerSource = KIN_ALERT<br/>❌ 不再向外示警
    }
```

---

## 9. 启动时序 —— 定价表构建

```mermaid
sequenceDiagram
    participant Init as ModInitializer
    participant Cfg as ConfigManager
    participant Reg as AdaptedMobRegistry
    participant LP as LootPriceProvider
    participant LT as LootTable（原版）
    participant PE as PricingEngine
    participant Cache as PriceCache

    Init->>Cfg: 加载 config
    Init->>Reg: 加载已适配列表（代码常量，38 个）
    Note over Init: 等待数据包加载完成<br/>（战利品表可能被数据包覆盖）
    Init->>LP: buildPriceTable(adaptedMobs)
    loop 每个已适配生物
        LP->>LT: table.pools() （record accessor）
        LT-->>LP: List<LootPool>
        LP->>LP: @Accessor 读 entries/conditions/functions
        LP->>LP: 计算 epk（期望产出）<br/>基准：玩家击杀 + looting 0
        LP->>PE: price(epk, cheap, rare, PRICE_MAX)
        PE-->>LP: 价格 + 单次产出数量
    end
    LP->>Cache: 写入缓存（EntityType → List<TradeSpec>）
    Note over Cache: 运行期只读，零反射开销
```

---

## 10. 模块依赖图

```mermaid
graph BT
    subgraph L4["L4 · 平台入口"]
        FI["FabricInitializer"]
        NI["NeoForgeInitializer"]
    end
    subgraph L3["L3 · Mixin 注入"]
        MM["MobMixin"]
        HM["LivingEntityHurtMixin"]
        LA["LootTableAccessor"]
    end
    subgraph L2["L2 · 领域逻辑"]
        AC["AngerController"]
        TB["TradeOfferBuilder"]
        RM["RestockManager"]
        NS["NeutralizationStrategy"]
    end
    subgraph L1["L1 · 基础设施"]
        CM["ConfigManager"]
        AR["AdaptedMobRegistry"]
        SC["NeutralizationScope"]
        PE["PricingEngine"]
        LP["LootPriceProvider"]
    end

    L3 --> L2
    L2 --> L1
    L4 --> L3
    L4 --> L1

    style L1 fill:#1a3a52,color:#fff
    style L2 fill:#2d5016,color:#fff
    style L3 fill:#5c4317,color:#fff
    style L4 fill:#4a1a52,color:#fff
```

**依赖规则：**
- L1 不依赖任何上层，可独立单测
- L2 只依赖 L1，业务逻辑与 MC API 解耦（便于单测）
- L3 是唯一接触 MC 内部实现的层，版本适配集中于此
- L4 平台专属，尽量薄

---

## 11. 定价曲线（ASCII，Mermaid 不适合数值曲线）

> 数据来自 `spikes/design-verify/final_pricing_128.json`，
> 110 个条目单调性 **100% 通过**，**零条目撞上限**。

```
价格
 ↑
128 ┤                                                   ╭── (epk=0.005)
    │                                             ╭─────╯
117 ┤                                        ╭────╯  ← 僵尸铁锭 (epk=0.0083)
    │                                  ╭─────╯
 94 ┤                            ╭─────╯  ← 骷髅头颅 (epk=0.025)
    │                      ╭─────╯
 63 ┤                ╭─────╯  ← 黏液球 (epk=0.105)
 62 ┤               ╭╯        ← 铜锭 (epk=0.11)
    │          ╭────╯
 39 ┤     ╭────╯              ← 蜘蛛眼/煤炭 (epk=0.333)
 30 ┤  ╭──╯                   ← 末影珍珠/烈焰棒 (epk=0.5)
 16 ┤╭─╯                      ← 腐肉/骨头/火药 (epk=1.0)
  7 ┤╯                        ← 旋风人棒 (epk=1.5)
  1 ┼──┬────┬────┬─────┬─────┬─────┬─────┬──→ epk（对数轴）
   2.0 1.0  0.5  0.11  0.025 0.01  0.005

    特性：产出每减半 → 价格稳定 +14.7 绿宝石
```

### 价格分布（110 条）

```
    1- 16 : 55  ███████████████████████████████████████████████████████
   17- 32 : 17  █████████████████
   33- 48 : 14  ██████████████
   49- 64 :  4  ████
   65- 80 :  7  ███████
   81- 96 :  3  ███
   97-112 :  1  █
  113-128 :  9  █████████

  撞上限(128)：0 个        撞下限(1)：11 个（红石等高产出物品）
```

### 代表性定价（实测）

| 生物 | 物品 | epk | 价格 | 单次产出 |
|------|------|-----|------|---------|
| 僵尸 | 铁锭 / 胡萝卜 / 马铃薯 | 0.0083 | **117** | 1 |
| 凋灵骷髅 | 凋灵骷髅头颅 | 0.0250 | **94** | 1 |
| 史莱姆 | 黏液球 | 0.1050 | 63 | 2 |
| 溺尸 | 铜锭 | 0.1100 | 62 | 1 |
| 凋灵骷髅 | 煤炭 | 0.3333 | 39 | 1 |
| 洞穴蜘蛛 | 蜘蛛眼 | 0.3333 | 39 | 1 |
| 末影人 | 末影珍珠 | 0.5000 | 30 | 1 |
| 烈焰人 | 烈焰棒 | 0.5000 | 30 | 1 |
| 潜影贝 | 潜影壳 | 0.5000 | 30 | 1 |
| 恶魂 | 恶魂之泪 | 0.5000 | 30 | 1 |
| 僵尸 | 腐肉 | 1.0000 | 16 | 2 |
| 骷髅 | 骨头 / 箭 | 1.0000 | 16 | 2 |
| 苦力怕 | 火药 | 1.0000 | 16 | 2 |
| 监守者 | 幽匿催发体 | 1.0000 | 16 | 1 |
| 旋风人 | 旋风人棒 | 1.5000 | 7 | 2 |
| 女巫 | 红石 | 6.0000 | 1 | 8 |

---

## 变更记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-09-11 | v1.0 | 首版：Context/Container/Component 三层 + 4 张时序图 + 状态机 + 模块依赖 |
