# Peace And Love — Spike 报告

- 项目：`peace-and-love`（Minecraft 1.21.1 Mod）
- 日期：2026-09-11
- 目的：验证 requirements 阶段识别的 3 个高风险项（R1 / R2 / R3），为 design 阶段提供事实依据
- 方法：全部基于 **1.21.1 官方 client.jar / server.jar + Mojang 官方 mappings** 的真实字节码与数据，不依赖推测

---

## 摘要

| Spike | 风险 | 结论 | 影响 |
|-------|------|------|------|
| **R1** | 战利品表定价 | ✅ **可行**，Mixin 面积约 7 个 Accessor | 110 个条目单调性 100% 通过 |
| **R2** | 交易能力注入 | ⚠️ **原判断被推翻** → 改推荐方案 A | 见下方「重要更正」 |
| **R3** | Goal vs Brain | ✅ **已量化**：Goal 25 个 / Brain 6 个 | v1.0 范围可决策 |

**产物清单：**

```
spikes/
├── r1-loot/
│   ├── fetch.py              下载 client.jar 并提取 100 张实体战利品表
│   ├── price_algo.py         v1（暴露 3 个缺陷）
│   ├── price_algo_v2.py      v2（修正 3 个，暴露第 4 个）
│   ├── price_algo_v3.py      v3（全量扫描 84 张有效表，最终版）
│   ├── v3_out.txt            完整输出（含 110 条定价表 + 单调性验证）
│   └── loot_tables/          100 张原版实体战利品表 JSON
├── r2-trade/
│   ├── analyze.py            Merchant 接口 / MerchantMenu / MerchantOffer 字节码分析
│   └── r2_out.txt            完整输出
└── r3-ai/
    ├── detect_ai.py          v1（判据有误）
    ├── classify_v2.py        v2（修正判据，最终版）
    ├── ai_system_map.json    59 个生物的原始判定数据
    ├── neutralization_plan.json  ★ 中立化分组结论（供 dev 阶段直接引用）
    ├── r3_out.txt / r3v2_out.txt  完整输出
    └── server_mappings.txt   官方 mappings（7.4 MB）
```

---

## R1 — 战利品表定价可行性 ✅

### 结论：可行，Mixin 面积极小

**无需 Mixin 的部分：**
- `LootTable` 在 1.21.1 中为 record，`pools` 有 public accessor
- `LootPool.entries()` 同为 public
- → **表结构遍历零成本**

**必须 Mixin `@Accessor` 的字段（约 7 个，单文件 ≤ 60 行）：**

| # | 目标 | 字段 | 用途 |
|---|------|------|------|
| ① | `LootPool` | `rolls` / `bonusRolls` (NumberProvider) | 抽取次数 |
| ② | `LootPoolSingletonContainer` | `functions` | 取 `set_count` |
| ③ | `LootPoolEntryContainer` | `conditions` | 取概率条件 |
| ④ | `LootItemRandomChanceCondition` | `probability` | 基础概率 |
| ⑤ | `LootItemRandomChanceWithEnchantedBonusCondition` | `unenchantedChance` | 稀有掉落概率 |
| ⑥ | `SetItemCountFunction` | `value` (NumberProvider) | 数量分布 |
| ⑦ | `LootItem` | `item` (Holder\<Item\>) | 物品标识 |

### 全量扫描结果（84 张有效实体表）

| entry type | 出现次数 | 处理 |
|-----------|---------|------|
| `item` | 110 | ✅ 可定价 |
| `empty` | 3 | 跳过 |
| `loot_table` | 2 | 需递归解析（远古守卫者/守卫者引用钓鱼表） |
| `tag` | 1 | 需展开 tag（苦力怕唱片） |

| condition | 次数 | 可静态求值 |
|-----------|------|-----------|
| `killed_by_player` | 19 | ✅ |
| `random_chance_with_enchanted_bonus` | 10 | ✅ |
| `damage_source_properties` | 5 | ⚠️ 运行时依赖 |
| `random_chance` | 4 | ✅ |
| `entity_properties` | 4 | ⚠️ 运行时依赖 |
| `inverted` | 2 | ✅ |

→ **不可静态求值的仅 8 个条目**（岩浆怪萤光体、掠夺者不祥之瓶、史莱姆球、海龟碗），采用保守衰减因子 0.3 + `price_overrides` 兜底。

### 迭代中修正的 4 个算法缺陷

这是 spike 的核心价值——**每个缺陷都会在真机上表现为「价格乱来」**：

| # | 缺陷 | 症状 | 修正 |
|---|------|------|------|
| ① | 线性反比 `Price = C/x` | 期望产出 ≤ 0.11 的条目**全部撞上价格上限 64**，稀有度完全无法区分 | 改对数曲线，把 ~2.6 个数量级压进 [1,64] |
| ② | `uniform` count 用 `(min+max)/2` | 凋灵骷髅煤炭 `uniform(-1,1)` 被算成**期望 0**（判为零产出 → 定天价） | 逐值 `clamp(≥0)` 后求期望 = 0.333，对齐 MC 实际行为 |
| ③ | `rolls` 当 float 读 | 女巫的 `rolls = uniform(1,3)` 直接抛 `TypeError` 崩溃 | 用统一的 NumberProvider 求期望函数 |
| ④ | 忽略 entry weight | 女巫木棍 `weight=2` 被当成与其他条目等概率 | 按 `weight/total_weight` 计算 |

### 定价结果验证

**单调性：✅ 110 个可交易条目全部满足「越稀有越贵」，零违反。**

抽样（`epk` = 每次击杀期望产出）：

| 物品 | epk | 价格 | 单次交易产出 |
|------|-----|------|-------------|
| 僵尸/铁锭·胡萝卜·马铃薯 | 0.0083 | **59** | 1 |
| 岩浆怪/岩浆膏 | 0.0131 | 54 | 1 |
| 凋灵骷髅/**骷髅头颅** | 0.0250 | **47** | 1 |
| 溺尸/铜锭 | 0.1100 | 31 | 1 |
| 女巫/发光石粉 | 0.2857 | 21 | 2 |
| 凋灵骷髅/煤炭 | 0.3333 | 20 | 1 |
| 末影人/**末影珍珠** | 0.5000 | 16 | 1 |
| 潜影贝/潜影壳 | 0.5000 | 16 | 1 |
| 僵尸/腐肉 | 1.0000 | 8 | 2 |
| 雪傀儡/雪球 | 7.5000 | 1 | 15 |

### 待 design 标定的参数

```
epk_cheap = 2.0     定价曲线廉价端锚点
epk_rare  = 0.005   定价曲线稀有端锚点
PRICE_MAX = 64      ⚠️ 关系 R13：骷髅头颅仅 47 绿宝石是否过低？
```

**FR-2.4 的「单次产出 = 一次击杀最大掉落数」可直接从 `set_count.max` 取得 ✅**

---

## R2 — 交易能力注入 ⚠️ 重要更正

### 🔄 原判断被字节码事实推翻

我在 requirements 阶段**倾向方案 B（自建 Menu）**，理由是「Architectury 无法屏蔽接口注入差异」。
**spike 结果显示这个判断不成立，现改为推荐方案 A。**

### 关键发现：`Merchant` 是纯行为接口，无字段依赖

```
net.minecraft.world.item.trading.Merchant → dbt (接口)
  必须实现的 abstract 方法：11 个
  有默认实现的方法：       3 个（含 canRestock）
```

11 个方法全部是**行为方法**，无一需要访问 private 字段：

| 方法 | 实现难度 |
|------|---------|
| `getTradingPlayer()` / `setTradingPlayer()` | 存一个字段即可 |
| `getOffers()` | 返回缓存的 MerchantOffers |
| `notifyTrade()` / `notifyTradeUpdated()` | 播音效 + 更新状态 |
| `showProgressBar()` | `return false`（怪物无等级条） |
| `getNotifyTradeSound()` | 返回一个 SoundEvent |
| `isClientSide()` | `return level().isClientSide` |
| `overrideXp()` / `overrideOffers()` | 空实现（怪物无经验交易） |
| `openTradingScreen()` | 有 **default 实现**，可直接复用 |

### `MerchantMenu` 的构造无障碍

```
构造器：(int, Inventory)                 ← 客户端用
        (int, Inventory, Merchant)      ← 服务端用，只需传一个 Merchant 实例
```

**public 字段**：`PAYMENT1_SLOT`、`PAYMENT2_SLOT`、`RESULT_SLOT`
→ 槽位常量可直接用，**无需 Accessor**

### `MerchantOffer` 原版已实现全部所需语义

```
private int uses;              ← FR-2.4 交易次数
private int maxUses;           ← FR-2.4 次数上限
private int demand;            ← 需求涨价（P2 可选）
private float priceMultiplier; ← 价格倍率
private int specialPriceDiff;  ← 特殊折扣
```

**构造器有 6 个重载**，其中 `(ItemCost, Optional<ItemCost>, ItemStack, int uses, int maxUses, float priceMultiplier)` 直接满足需求。
→ **交易次数、上限、补货语义完全不用自己写。**

### ✅ 追加验证：每日补货可直接用原版机制表达

> 用户提问：「每天一次能否通过补货频率控制？实际想要的效果是每天最多购买到单次击杀时能获取的掉落物上限」
> **结论：成立，且比先前设计更简单。**

`MerchantOffer` 实测字段（内层 jar 字节码）：

```
private       int   uses               ★ 已用次数
private final int   maxUses            ★ 次数上限
private       int   demand
private final float priceMultiplier
private       int   specialPriceDiff
private final int   xp
private final boolean rewardExp
```

配套方法：`resetUses()` / `increaseUses()` / `isOutOfStock()` / `getUses()` / `getMaxUses()` / `setToOutOfStock()`

`Villager` 侧补货机制：

```
restock()                   批量把 uses 清零
shouldRestock()             判断补货时机
needsToRestock()            是否有 offer 已售罄
lastRestockGameTime         上次补货的游戏时间
numberOfRestocksToday       当天已补货次数
lastRestockCheckDayTime     上次检查补货的日时间
```

因此：

```
maxUses = 1  +  每游戏日补货一次
≡ 「每天最多买到一次击杀能拿到的量」
```

**❌ 先前设想的 `Map<ItemId, lastTradeDay>` 是多余的，已撤销。** 实体 NBT 只需存一个 `long lastRestockDay`。

**实现要点：**
1. 生成 offer 时 `maxUses = 1`（配置项 `max_uses_per_day`，默认 1）
2. `result` 数量 = 该掉落物「一次击杀最大掉落数」（R1 已能算出）
3. 自实现 `shouldRestock()`：`currentDay > lastRestockDay` 则补货，周期为配置项 `restock_interval_days`（默认 1）
4. ⚠️ **不能直接调用 `Villager.restock()`** —— 它耦合了 gossip / demand / 价格波动，需自写精简版 `resetAllUses()`

**额外收益**：补货周期成为纯配置项，管理员可直接调节整个经济节奏而无需改代码。

### ⚠️ spike 过程中修正的两个脚本缺陷

| # | 缺陷 | 说明 |
|---|------|------|
| ① | 新写的 `verify_restock.py` 直接读外层 jar | 1.21.1 server.jar 是 **bundler 壳**，真正的 MC 类在 `META-INF/versions/1.21.1/server-1.21.1.jar` 内层根目录（6128 个 .class）。**原始的 `analyze.py` / `detect_ai.py` 处理正确，先前 R2/R3 结论不受影响** |
| ② | 自写的 class 常量池解析器返回 None | 已改为复用 `analyze.py` 中验证可用的 `parse_class` |

### 方案对比（修正后）

| 维度 | 方案 A（注入 Merchant） | 方案 B（自建 Menu） |
|------|----------------------|-------------------|
| GUI 工作量 | **零**（复用原版村民界面） | 需自写 Screen（贴图/布局/滚动） |
| 网络同步 | **零**（原版 MerchantMenu 已有） | 需自写包与同步 |
| 交易次数/补货语义 | **零**（MerchantOffer 已有 uses/maxUses） | 需自己实现 |
| 客户端是否必装 | 可能不必（走原版包） | **必须** |
| 跨端差异 | 接口注入方式不同（Fabric `@Implements` vs NeoForge Mixin+AT） | MenuType 注册有统一 API |
| 与其他模组冲突面 | 较大（注入 Mob 基类） | 较小 |
| **总工作量** | **显著更低** | 高 |

### 修正后的建议：**方案 A**

理由：
1. `Merchant` 无字段依赖，11 个方法全是行为方法 → 注入成本远低于预估
2. `MerchantOffer` 已实现 `uses`/`maxUses`/`priceMultiplier`，FR-2.4 几乎零成本
3. `openTradingScreen` 有 default 实现，GUI 完全免费
4. 原版 `AbstractVillager` 提供可照抄的参考实现

**残留待验证（design 阶段最小原型）：**
- ⚠️ NeoForge 的 Mixin 接口注入是否需要 Access Transformer 配置
- ⚠️ 注入到 `Mob` 基类 vs 只注入目标类（`Zombie`/`Skeleton` 等 25 个）—— 后者更安全但代码量大，建议注入 `Mob` + 运行时白名单判定
- ⚠️ 客户端不装模组时能否正常交易（若能，是重要卖点）

---

## R3 — AI 系统适配 ✅ 已量化（v3 修正）

### ⚠️ 三次判据修正

| 版本 | 错误 | 后果 | 发现方式 |
|------|------|------|---------|
| v1 | 把 `customServerAiStep` 当 Brain 标志 | 误判末影人/烈焰人/幻翼/卫道士/唤魔者/凋灵 | 自查 |
| v2 | 「默认在白名单」= 「零工作量」 | **漏算 8 个生物的适配工作** | **用户指出** |
| v3 | 二分法「不是 Brain 就是 Goal」 | 误判末影龙（实为第三类） | 自查后字节码验证 |

### ★ 关键修正：白名单 ≠ 零工作量

**白名单是运行时配置项，管理员可随时移出。** 移出后代码必须能正常工作，否则就是 bug。

因此 **39 个主动敌对生物全部需要实现中立化逻辑**，白名单只决定默认是否启用。

### v3 正确判据（三分法，字节码实测）

| 系统 | 判据 | 数量 |
|------|------|------|
| ① **Goal** | 覆写 `registerGoals()` 且引用 `goalSelector`/`targetSelector` | **32** |
| ② **Brain** | 覆写 `makeBrain()`/`brainProvider()` | **6** |
| ③ **自有 AI** | 以上皆非 | **1** |

### 实测继承链与引用情况

```
末影龙      EnderDragon → Mob → LivingEntity → Entity
            ❌ 均未引用 goalSelector/targetSelector
            ✅ 引用 EnderDragonPhaseManager（Phase 系统）

凋灵        WitherBoss → Monster → PathfinderMob → Mob → ...
            ✅ 引用 goalSelector, targetSelector, 覆写 registerGoals

潜影贝      Shulker → AbstractGolem → PathfinderMob → Mob → ...
            ✅ 引用 goalSelector, targetSelector, 覆写 registerGoals

幻翼        Phantom → FlyingMob → Mob → LivingEntity → Entity
            ✅ 引用 goalSelector, targetSelector, 覆写 registerGoals

恼鬼        Vex → Monster → PathfinderMob → Mob → ...
            ✅ 引用 goalSelector, targetSelector, 覆写 registerGoals

僵尸(对照)  Zombie → Monster → PathfinderMob → Mob → ...
            ✅ 引用 goalSelector, targetSelector, 覆写 registerGoals
```

> 📌 **凋灵先前被我归为「Boss 天然跳过」是错的** —— 它走标准 Goal 系统，
> 与僵尸的处理方式相同（只是 target 选择在 `customServerAiStep` 另有硬编码逻辑需一并处理）。
> **真正特殊的只有末影龙一个。**

### 最终分组（39 个，全部需实现）

| 系统 | 数量 | 生物 |
|------|------|------|
| **Goal** | **32** | 僵尸、僵尸村民、尸壳、溺尸、僵尸猪灵、骷髅、凋灵骷髅、流浪者、沼骸、巨人、蜘蛛、洞穴蜘蛛、苦力怕、恶魂、烈焰人、女巫、史莱姆、岩浆怪、末影人、末影螨、守卫者、远古守卫者、幻术师、劫掠兽、蠹虫、**潜影贝、幻翼、掠夺者、卫道士、唤魔者、恼鬼、凋灵** |
| **Brain** | **6** | 猪灵、猪灵蛮兵、疣猪兽、僵尸疣猪兽、监守者、旋风人 |
| **自有 AI** | **1** | 末影龙 |

### 需超出标准改写的特殊适配（8 个）

| 生物 | 系统 | 难点 |
|------|------|------|
| 潜影贝 | Goal | 固定在方块上，索敌内嵌于 `ShulkerAttackGoal`，无移动 Goal |
| 幻翼 | Goal | 用 `PhantomAttackPlayerTargetGoal`；另有「玩家不睡觉才生成」条件 |
| 掠夺者 | Goal | 袭击系统，需处理 `Raider.canJoinRaid` |
| 卫道士 | Goal | 袭击系统；Johnny 名牌特殊行为 |
| 唤魔者 | Goal | 袭击系统；召唤恼鬼/唤魔尖牙，召唤物需一并处理 |
| 恼鬼 | Goal | 有 owner 概念，生命周期绑定唤魔者 |
| 凋灵 | Goal | target 选择在 `customServerAiStep` 中另有硬编码 |
| **末影龙** | **自有 AI** | **Phase 系统，标准 Goal 改写完全不适用，需独立方案** |

### 工作量重估

```
v2（错误）：Goal 25 + Brain 6 + 白名单 6「零」+ Boss 2「零」= 实现 31 个
v3（修正）：Goal 32 + Brain 6 + 自有 AI 1                  = 实现 39 个
```

增量小于「+8 个生物」的直觉估计：
- 袭击系 3 个（掠夺者/卫道士/唤魔者）共享 `Raider` 基类，可一并处理
- 恼鬼依附唤魔者，处理完唤魔者后成本很低
- 凋灵走标准 Goal，成本接近普通生物
- **真正独立的只有：潜影贝、幻翼、末影龙 3 个**

### Boss 处理建议

不是「不用做」，而是「做出来后交易 UI 对 Boss 意义不大」：
- 仍实现中立化逻辑，保证管理员移出白名单时生效
- 对 Boss 不生成交易 offer，或提供独立开关 `boss_trading_enabled`（默认 false）
- ⚠️ **末影龙的 Phase 系统适配成本最高，design 阶段需单独评估是否纳入 v1.0**

---

## 对 requirements 与 RISKS 的影响

### ✅ 用户已裁定的决策（2026-09-11）

| 项 | 决策 |
|---|---|
| v1.0 范围 | **方案 B —— 全部实现**（Goal 32 + Brain 6 + 自有 AI 1） |
| 监守者 | **不进**默认白名单，中立化并可交易 |
| `PRICE_MAX` | 默认 **128**，管理员可配置 |
| 定价锚点 | `cheap=2.0` / `rare=0.005` 为默认值，管理员可调 |
| 交易频次 | `maxUses=1` + 每游戏日补货，两者均可配置 |
| 白名单语义 | **运行时配置**，移出后代码必须能工作 → 全部生物都要适配 |

> `PRICE_MAX=128` 正好卡在 `MerchantOffer` 双槽上限（`baseCostA` + `costB`，64+64），
> **不需要绿宝石块换算**，技术上最干净。骷髅头颅 47 → 94 绿宝石。

### 需要修改的文档内容

| 文档 | 位置 | 修改 |
|------|------|------|
| `RISKS.md` | R1 | ✅ 已降级 🔴H → 🟢L |
| `RISKS.md` | R2 | ✅ 已降级 🔴H → 🟡M，推荐方案更正为 A |
| `RISKS.md` | R3 | ✅ 已降级 🔴H → 🟡M，v3 修正分组 |
| `RISKS.md` | R8 | ✅ 已降级 🟡M → 🟢L |
| `01-requirements.md` | 5.1 | ⏳ 更新架构决策 3 的推荐方案（B → A） |
| `01-requirements.md` | FR-1.5 | ⏳ 白名单语义澄清：运行时配置，非「不实现」 |
| `01-requirements.md` | FR-2.4 | ⏳ 交易次数改为 `maxUses=1` + 每日补货 |
| `01-requirements.md` | 4.3 | ⏳ 客户端是否必装取决于 P2 验证结果 |
| `01-requirements.md` | 配置项 | ⏳ 新增 `price_max`、`epk_cheap`、`epk_rare`、`max_uses_per_day`、`restock_interval_days`、`boss_trading_enabled` |

### 仍待 design 阶段决策

- [ ] **末影龙是否纳入 v1.0**？其 Phase 系统需独立适配方案，成本最高
- [ ] Boss 交易开关的默认值（建议 `boss_trading_enabled = false`）

---

## 复现方式

```bash
cd D:/Coding/projects/peace-and-love/spikes

# R1：下载 client.jar，提取战利品表，跑定价算法
cd r1-loot && python fetch.py && python price_algo_v3.py

# R3：下载 server.jar + mappings，判定 AI 系统
cd ../r3-ai && python detect_ai.py && python classify_v2.py

# R2：分析 Merchant 接口与相关类字节码
cd ../r2-trade && python analyze.py
```

依赖：仅 Python 标准库（`zipfile` / `struct` 手工解析 class 常量池）
下载物：client.jar 26 MB、server.jar 51 MB、mappings 7.4 MB（已缓存，不重复下载）

---

## 变更记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-09-11 | v1.0 | R1/R2/R3 spike 完成。R1 可行；R2 原判断被推翻改推荐方案 A；R3 完成量化分组 |
| 2026-09-11 | v1.1 | 追加验证补货机制：`maxUses=1` + 每日补货即可表达「每天限一次击杀量」，撤销 `Map<ItemId,day>` 设计。R3 v3 修正：白名单≠零工作量，全部 39 个生物需适配；末影龙实为第三类自有 AI（Phase 系统），凋灵实为标准 Goal。修正两个脚本缺陷（bundler jar 结构、class 解析器） |
