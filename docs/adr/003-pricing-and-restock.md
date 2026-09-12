# ADR-003: 对数定价曲线 + `MerchantOffer` 原生次数机制

## 状态

Accepted（2026-09-11）

## 背景

需求要求（`../01-requirements.md` FR-2.2 / FR-2.3）：

1. 每种掉落物的绿宝石价格与其**稀有度**挂钩 —— 越难拿的越贵
2. 每个怪物的每种掉落物**每游戏日只能交易 1 次**，单次产出等于原版一次击杀的最大掉落量
3. 平衡基准为**无绿宝石农场**（绿宝石农场属高成本生电机器，不能假设玩家拥有）
4. 定价参数与补货周期均需**管理员可配置**

两个子问题必须分别解决：**价格怎么算**、**次数怎么限**。

---

## 决策一：价格用对数曲线

```
epk   = 期望每次击杀产出量（expected per kill，玩家击杀 + looting 0 为基准）
pos   = log(cheap / epk) / log(cheap / rare)          // 归一化到 [0,1]
price = clamp(round(1 + (PRICE_MAX - 1) × pos), 1, PRICE_MAX)
```

默认参数（**全部可配置**）：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `PRICE_MAX` | **128** | 价格上限 |
| `epk_cheap` | **2.0** | 廉价锚点：epk ≥ 此值时价格为 1 |
| `epk_rare` | **0.005** | 稀有锚点：epk ≤ 此值时价格为 PRICE_MAX |

### 为什么是 128

`MerchantOffer` 有两个输入槽（`baseCostA` + `costB`），各自上限 64，合计 **128**。选 128 正好用满原版槽位，**不需要引入绿宝石块换算**，技术上最干净。

### 曲线性质

产出每减半 → 价格稳定增加约 `(128-1) / log2(2.0/0.005) ≈ 14.7` 绿宝石。
即"等比稀有度 → 等量价格"，这正是定价直觉所期待的。

### 实测验证

对 1.21.1 全部 84 张有效战利品表、110 个可定价条目重算：

- **单调性 110/110 通过**（epk 越小价格必然越高或相等）
- **撞上限 0 个** —— 对比线性反比方案 `16/epk` 在 23 个测试条目中有 7 个撞顶
- 撞下限 11 个（红石等高产出物品，符合预期）

价格分布：

```
    1- 16 : 55 条    ← 常见掉落物
   17- 32 : 17 条
   33- 48 : 14 条
   49- 64 :  4 条
   65- 80 :  7 条
   81- 96 :  3 条    ← 凋灵骷髅头颅 94
   97-112 :  1 条
  113-128 :  9 条    ← 僵尸铁锭/胡萝卜/马铃薯 117
```

---

## 决策二：次数限制复用 `MerchantOffer` 原生机制

```
maxUses = 1  +  每游戏日补货一次  ≡  「每天最多买到一次击杀的量」
```

### 实测依据（1.21.1 `MerchantOffer` 字段）

```java
private       int    uses;              // ★ 已用次数
private final int    maxUses;           // ★ 次数上限
private       int    demand;
private final float  priceMultiplier;
// 方法
public int     getUses();
public void    resetUses();             // ★ 补货即调用此方法
public int     getMaxUses();
public void    increaseUses();
public boolean isOutOfStock();
public void    setToOutOfStock();
```

`Villager` 侧的补货机制同样现成：`restock()`、`shouldRestock()`、`lastRestockGameTime`、`numberOfRestocksToday`。

### 实体只需新增一个字段

```java
long lastRestockDay;   // 上次补货的游戏日
```

判定逻辑：

```java
long currentDay = level.getDayTime() / 24000L;
if (currentDay - lastRestockDay >= config.restockIntervalDays) {
    offers.forEach(MerchantOffer::resetUses);
    lastRestockDay = currentDay;
}
```

补货周期 `restock_interval_days` 可配置：`1` = 每天，`3` = 三天一次，管理员可直接调节整个经济节奏。

---

## 后果

### 正面

- 定价对全部 110 个条目单调、零撞顶，且**新增生物自动适配**（无需人工维护价格表）
- 只有 2 个锚点参数，管理员心智负担低
- 次数机制**零自建代码**：NBT 持久化、客户端"售罄"显示全部由原版 CODEC 与 GUI 免费提供
- 补货周期成为纯配置项，经济节奏可调

### 负面

- ⚠️ **不能直接调用 `Villager.restock()`** —— 它耦合了 gossip（村民闲聊声望）、`demand`（需求量影响价格）和价格波动逻辑，必须自写精简版 `resetAllUses()`
- ⚠️ 必须固定 `priceMultiplier = 0`，否则原版的需求量机制会让价格随交易次数漂移，破坏定价确定性
- 锚点外的极端值会被 clamp，超稀有物品之间不再区分（缓解：提供 `price_overrides` 手工修正表）
- 单笔价格上限固定为 128，若管理员想要更高价格需改用绿宝石块（v1.0 不支持）

### 中性

- epk 以"玩家击杀 + looting 0"为基准计算。装备抢夺附魔的玩家击杀收益会高于交易，这是有意为之 —— 战斗仍应有其回报

---

## 备选方案

### 价格算法

**线性反比 `price = k / epk`**
- 优点：公式最简单，只有 1 个系数
- 缺点：**23 个测试条目中 7 个撞上限**，稀有区间完全失去分辨率（骷髅头颅与僵尸铁锭都是 64，但实际稀有度差 3 倍）
- 不选的原因：产出跨度达 900 倍（红石 6.0 vs 铁锭 0.0083），而价格槽只有 128 档，线性映射必然在稀有端饱和

**分段查表**
- 优点：完全可控，可人工微调每个物品
- 缺点：需手工维护 110+ 条目；新增生物或数据包自定义战利品表时无法自动适配；单调性靠人工保证
- 不选的原因：违反"支持数据包自定义"的需求

### 次数限制

**自建 `Map<ItemId, lastTradeDay>` 存于实体 NBT**
- 优点：语义直接对应需求描述
- 缺点：需自写 NBT 序列化；客户端"售罄"状态需自己同步；与 `MerchantOffer` 已有机制重复
- 不选的原因：**实测发现原版机制已完全覆盖此语义**。这是 requirements 阶段的设计冗余，spike 后撤销

**只用 `maxUses` 不做补货**
- 缺点：`maxUses` 是持久化的**总次数**，不是每日次数 —— 用完即永久售罄，不符合需求
- 不选的原因：语义错误

---

## 参考资料

- 定价实测：`spikes/design-verify/reprice.py` → `final_pricing_128.json`（110 条）
- 曲线可视化：`spikes/r1-loot/explain_curve.py`
- 经济模型测算：`spikes/r1-loot/economy_model.py`
- `MerchantOffer` 字节码验证：`spikes/r2-trade/verify_restock.py`
