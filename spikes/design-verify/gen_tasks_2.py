"""
批量生成 03-tasks/ 第二批：PRICE / TRADE / NEUT
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent.parent / "03-tasks"
OUT.mkdir(exist_ok=True)

TPL = """# {tid}: {title}

**状态：** todo
**优先级：** {prio}
**预估：** {est}
**Owner：** {owner}
**依赖：** {deps}
**可并行：** {para}

## 目标

{goal}

## 来源

{src}

## 验收标准

{accept}

## 技术要点

{tech}

## 产出物

{output}

## 备注

{note}
"""

T = []


def add(tid, title, prio, est, owner, deps, para, goal, src, accept, tech, output, note="无"):
    T.append(dict(tid=tid, title=title, prio=prio, est=est, owner=owner,
                  deps=deps, para=para, goal=goal, src=src,
                  accept=accept, tech=tech, output=output, note=note))


# ─────────────── PRICE ───────────────
add("T-PRICE-001", "LootTableScanner 解析战利品表算 epk", "P0", "6h", "agent",
    "T-SETUP-003", "T-CFG-002",
    "扫描 38 个生物的原版战利品表，计算每个掉落物的「每击杀期望产出」(epk)。",
    "- 设计：`02-design.md` §3.3 定价引擎、§5.1 启动时构建定价表\n- 决策：`02-adr/003`\n- spike：`spikes/r1-loot/price_algo_v3.py`",
    """- [ ] 解析出 **110 条**「生物 × 掉落物」条目
- [ ] epk 计算含抽取概率、数量范围期望、多池叠加
- [ ] 排除稀有掉落中的装备类（不参与交易）
- [ ] 与 spike 产出的 `final_pricing_128.json` 逐条比对，epk 一致
- [ ] 解析失败的生物打 WARN 但不崩服""",
    """**服务端启动后**执行（战利品表在 `ReloadableServerResources` 就绪后才可读）。
监听 `ServerLifecycleEvents` 或 Architectury 的等价事件。

epk 公式：`epk = Σ(pool_rolls × entry_weight/total_weight × E[count])`
注意 `LootItemConditions` 中的 `killed_by_player` 与 `looting` 加成不计入基准 epk。""",
    "- 代码：`pricing/LootTableScanner.java`\n- 测试：`LootTableScannerTest.java`\n- Commit：`feat(pricing): 实现战利品表解析与 epk 计算`",
    "spike 阶段已验证算法可行，本任务是把 Python 原型翻译为 Java。")

add("T-PRICE-002", "PriceCalculator 对数曲线", "P0", "3h", "agent",
    "T-PRICE-001", "T-CFG-003",
    "实现 epk → 价格的对数映射曲线。",
    "- 设计：`02-design.md` §3.3\n- 决策：`02-adr/003`",
    """- [ ] `pos = log(epk_cheap/epk) / log(epk_cheap/epk_rare)`
- [ ] `price = 1 + (price_max-1) × pos`，clamp 到 [1, price_max]
- [ ] `epk_cheap` / `epk_rare` / `price_max` 全部从配置读取
- [ ] 单调性：epk 越小价格越高
- [ ] 边界：epk ≥ cheap 时价格 = 1；epk ≤ rare 时价格 = price_max""",
    """分母 `log(2/0.005) ≈ 5.99`（默认参数）。
用 `Math.log` 而非 `Math.log10`，两者比值等价但保持与 spike 一致。
结果取整用 `Math.round`。""",
    "- 代码：`pricing/PriceCalculator.java`\n- 测试：`PriceCalculatorTest.java`\n- Commit：`feat(pricing): 实现对数定价曲线`")

add("T-PRICE-003", "PriceTable 启动时构建与缓存", "P0", "3h", "agent",
    "T-PRICE-002", "T-TRADE-001",
    "在服务端启动与配置重载时构建定价表并缓存，供交易系统查询。",
    "- 设计：`02-design.md` §5.1",
    """- [ ] 服务端启动完成后自动构建
- [ ] `/peaceandlove reload` 后重建
- [ ] 查询 `getPrice(EntityType, Item)` 为 O(1)
- [ ] 构建耗时打 INFO 日志（性能基线）
- [ ] 表为不可变，构建后不可修改""",
    "用 `Map<EntityType<?>, Map<Item, Integer>>` 或扁平化 record key。\n构建应在主线程完成，避免与交易请求竞态。",
    "- 代码：`pricing/PriceTable.java`\n- Commit：`feat(pricing): 实现定价表构建与缓存`")

add("T-PRICE-004", "定价单调性自检", "P1", "2h", "agent",
    "T-PRICE-003", "T-TRADE-002",
    "启动时自检定价表的单调性与边界，异常时打 WARN 提醒管理员参数配置不当。",
    "- 设计：`02-design.md` §3.3",
    """- [ ] 检测同一生物内「epk 更小但价格更低」的逆序对
- [ ] 检测撞上限/下限的条目数并打 INFO
- [ ] 逆序对存在时打 WARN 并列出前 5 个
- [ ] 自检本身不阻断启动""",
    """spike 实测默认参数下 **110/110 单调、0 撞上限、11 撞下限**（红石等高产出）。
若管理员改了 `epk_cheap`/`epk_rare` 导致大量撞顶，此检查会提示。""",
    "- 代码：`pricing/PriceTable.java`（自检方法）\n- Commit：`feat(pricing): 添加定价单调性自检`")

# ─────────────── TRADE ───────────────
add("T-TRADE-001", "MobMerchantMixin 注入 Merchant 接口", "P0", "5h", "agent",
    "T-SCOPE-002", "T-NEUT-001",
    "通过 Mixin 向 `Mob` 基类注入 `Merchant` 接口，实现全部 10 个 abstract 方法。",
    "- 设计：`02-design.md` §4.1\n- 决策：`02-adr/002`\n- 验证：`P1-P4-VERIFY.md` P1",
    """- [ ] `@Mixin(Mob.class) implements Merchant` 编译通过
- [ ] 实现 10 个 abstract 方法（见技术要点）
- [ ] `@Unique` 字段前缀 `pal$`
- [ ] `getOffers()` 懒加载，非目标生物永远返回空
- [ ] **双端**运行时 `Merchant.isAssignableFrom(Mob.class) == true`
- [ ] 不需要 Access Transformer（accesswidener 保持空）""",
    """**`Merchant` 共 12 个方法 = 10 abstract + 2 default**（字节码实测，勿凭印象）：

10 个必须实现：
```java
void setTradingPlayer(Player)
Player getTradingPlayer()
MerchantOffers getOffers()
void overrideOffers(MerchantOffers)
void notifyTrade(MerchantOffer)
void notifyTradeUpdated(ItemStack)
int getVillagerXp()
void overrideXp(int)
boolean showProgressBar()
SoundEvent getNotifyTradeSound()
```

2 个 default **可直接白嫖，不要重写**：
```java
boolean isClientSide()
void openTradingScreen(Player, Component, int)   // ★ 整套 GUI 流程免费
```

字段（3 个）：`pal$tradingPlayer` / `pal$offers` / `pal$lastRestockDay`。""",
    "- 代码：`mixin/MobMerchantMixin.java`\n- Commit：`feat(trade): Mixin 注入 Merchant 接口`",
    "P1 已在真实 NeoForge 服务端验证注入成功，本任务是把探针代码正式化。")

add("T-TRADE-002", "TradeOfferBuilder 构建交易列表", "P0", "4h", "agent",
    "T-PRICE-003, T-TRADE-001", "T-NEUT-002",
    "根据生物类型与定价表构建 `MerchantOffers`，每个掉落物一条交易。",
    "- 设计：`02-design.md` §3.4 交易规格",
    """- [ ] 输入槽为绿宝石，数量 = 定价表价格
- [ ] 价格 > 64 时拆分为两槽（如 117 = 64 + 53）
- [ ] 输出槽为掉落物，数量按设计取值
- [ ] `maxUses = 1`（每日 1 次）
- [ ] `xp = 0`（不给经验，非村民）
- [ ] 白名单内或未适配生物返回空列表""",
    """`MerchantOffer(ItemCost baseCostA, Optional<ItemCost> costB, ItemStack result, int maxUses, int xp, float priceMultiplier)`

1.21.1 用 `ItemCost` 而非旧版 `ItemStack`。
价格上限 128 正是因为双槽 64+64。""",
    "- 代码：`trade/TradeOfferBuilder.java`\n- 测试：`TradeOfferBuilderTest.java`\n- Commit：`feat(trade): 实现交易列表构建`")

add("T-TRADE-003", "右键交互打开交易界面", "P0", "3h", "agent",
    "T-TRADE-001", "T-TRADE-004",
    "玩家右键中立化生物时打开交易 GUI，复用原版 `openTradingScreen`。",
    "- 设计：`02-design.md` §3.4\n- 需求：FR-2.2",
    """- [ ] 右键中立化生物打开交易界面
- [ ] 白名单内/未适配生物右键无反应（保持原版行为）
- [ ] `trading_enabled=false` 时不开界面
- [ ] Boss 且 `boss_trading_enabled=false` 时不开界面
- [ ] 处于仇恨状态的生物不开界面
- [ ] 空手右键才触发，持物品时不拦截原版交互""",
    """在 `Mob#mobInteract` 注入，返回 `InteractionResult.sudo`。
**服务端权威**：`if (level().isClientSide) return InteractionResult.SUCCESS;`

直接调 `openTradingScreen(player, getDisplayName(), 0)`，
这是 default 方法，内部走原版 `MerchantMenu` + `ClientboundMerchantOffersPacket`。""",
    "- 代码：`mixin/MobMerchantMixin.java`\n- Commit：`feat(trade): 实现右键打开交易界面`")

add("T-TRADE-004", "RestockManager 每日补货", "P0", "4h", "agent",
    "T-TRADE-002", "T-TRADE-005",
    "每游戏日重置交易次数，自写 `resetAllUses()`，禁用 `Villager.restock()`。",
    "- 设计：`02-design.md` §5.3 每日补货\n- 决策：`02-adr/003`",
    """- [ ] 游戏日推进时（24000 tick）重置所有 offer 的 uses
- [ ] `restock_interval_days` 支持小数（如 0.5 = 半天）
- [ ] **不得调用 `Villager.restock()`**（会引入 gossip/demand 副作用）
- [ ] 补货判定基于 `level.getGameTime()`，非真实时间
- [ ] 玩家不在线期间的补货在实体加载时补算""",
    """```java
long currentDay = level.getGameTime() / 24000L;
if (currentDay - pal$lastRestockDay >= intervalDays) {
    offers.forEach(MerchantOffer::resetUses);   // 自写，非 restock()
    pal$lastRestockDay = currentDay;
}
```
`resetUses()` 是 `MerchantOffer` 的 public 方法，spike 已验证存在。""",
    "- 代码：`trade/RestockManager.java`\n- 测试：`RestockManagerTest.java`（边界：跨日、小数间隔）\n- Commit：`feat(trade): 实现每日补货机制`")

add("T-TRADE-005", "NBT 持久化", "P0", "3h", "agent",
    "T-TRADE-004", "T-NEUT-004",
    "把 `lastRestockDay` 与已生成的 offers 存入实体 NBT，跨存档保持。",
    "- 设计：`02-design.md` §3.4",
    """- [ ] `pal$lastRestockDay` 写入 NBT（key: `PalLastRestockDay`）
- [ ] offers 序列化（复用 `MerchantOffers#createTag`）
- [ ] 读档后交易次数状态正确恢复
- [ ] 旧存档（无该 NBT）不报错，按首次生成处理
- [ ] 白名单内生物不写入冗余 NBT""",
    """在 `Mob#addAdditionalSaveData` / `readAdditionalSaveData` 注入。
NBT 体积控制：offers 可选择**不持久化**，读档后按定价表重建，
只存 `lastRestockDay` + 各 offer 的 uses 计数，更省空间。设计倾向后者。""",
    "- 代码：`mixin/MobMerchantMixin.java`\n- Commit：`feat(trade): 实现交易状态 NBT 持久化`")

# ─────────────── NEUT ───────────────
add("T-NEUT-001", "NeutralizeStrategy 接口与 GoalSnapshot", "P0", "3h", "agent",
    "T-SCOPE-002", "T-TRADE-001",
    "定义中立化策略接口与 Goal 快照结构，为可逆还原打基础。",
    "- 设计：`02-design.md` §3.5 中立化策略\n- 决策：`02-adr/004`",
    """- [ ] `NeutralizeStrategy` 含 `neutralize(Mob)` / `restore(Mob)` / `supports(EntityType)`
- [ ] `GoalSnapshot` 记录被移除 Goal 的 `priority` + `Goal` 实例
- [ ] 快照可原样恢复到 `GoalSelector`
- [ ] 策略注册表按 EntityType 分派""",
    """`WrappedGoal.getGoal()` 与 `getPriority()` 均为 **public**（spike 已验证），
因此无需反射即可做快照。

```java
record GoalSnapshot(int priority, Goal goal) {}
```""",
    "- 代码：`neutralize/NeutralizeStrategy.java`、`neutralize/GoalSnapshot.java`\n- Commit：`feat(neutralize): 定义中立化策略接口`")

add("T-NEUT-002", "GoalBasedStrategy（32 个 Goal 系）", "P0", "6h", "agent",
    "T-NEUT-001", "T-NEUT-003",
    "对 32 个 Goal 系生物移除攻击类 Goal 与索敌类 TargetGoal。",
    "- 设计：`02-design.md` §3.5\n- 决策：`02-adr/004`",
    """- [ ] 用 `goalSelector.removeAllGoals(Predicate)` 移除攻击 Goal
- [ ] 用 `targetSelector.removeAllGoals(Predicate)` 移除索敌 Goal
- [ ] 移除前快照，支持 `restore()`
- [ ] **保留** `HurtByTargetGoal`（受击反击是设计要求）
- [ ] 生物不再主动接近/攻击玩家
- [ ] 移除操作幂等（重复调用不产生副作用）""",
    """`GoalSelector.removeAllGoals(Predicate<Goal>)` **存在且 public**（spike 字节码验证）。

需移除的 Goal 类型：
- `MeleeAttackGoal` / `RangedAttackGoal` / `RangedBowAttackGoal` / `RangedCrossbowAttackGoal`
- `NearestAttackableTargetGoal`（索敌玩家的那条）

**不要移除** `HurtByTargetGoal` —— 受击反击由 ANGER 模块统一控制。""",
    "- 代码：`neutralize/GoalBasedStrategy.java`\n- Commit：`feat(neutralize): 实现 Goal 系中立化策略`")

add("T-NEUT-003", "BrainBasedStrategy（6 个 Brain 系）", "P0", "6h", "agent",
    "T-NEUT-001", "T-NEUT-002",
    "对 6 个 Brain 系生物每 tick 擦除 `ATTACK_TARGET` memory。",
    "- 设计：`02-design.md` §5.2 Brain 系每 tick 拦截\n- 决策：`02-adr/004`",
    """- [ ] 覆盖猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽/监守者/旋风人
- [ ] 每 tick 检查并擦除 `MemoryModuleType.ATTACK_TARGET`
- [ ] 仇恨状态下**不擦除**（允许反击）
- [ ] `restore()` 停止擦除
- [ ] 性能：单实体每 tick 开销 < 1μs，做基线测量""",
    """```java
brain.eraseMemory(MemoryModuleType.ATTACK_TARGET);
brain.eraseMemory(MemoryModuleType.ANGRY_AT);   // 猪灵系
```

⚠️ **性能风险**（RISKS R?）：每 tick 拦截在大量实体时可能有开销。
先做基线：100 只生物同时加载，测 tick 耗时增量。超标改用事件驱动。""",
    "- 代码：`neutralize/BrainBasedStrategy.java`\n- Commit：`feat(neutralize): 实现 Brain 系中立化策略`",
    "⚠️ 风险任务：性能需实测基线。")

add("T-NEUT-004", "restore() 可逆还原", "P0", "4h", "agent",
    "T-NEUT-002, T-NEUT-003", "T-TRADE-005",
    "白名单移入时把生物还原为原版行为，保证配置热重载完全可逆。",
    "- 设计：`02-design.md` §3.5\n- 需求：FR-1.4（用户确认可逆为必需）",
    """- [ ] Goal 系从快照恢复 Goal 与 priority
- [ ] Brain 系停止 memory 擦除
- [ ] 还原后生物行为与原版**完全一致**
- [ ] 还原后交易能力移除（右键无反应）
- [ ] 反复 neutralize/restore 10 次无状态泄漏
- [ ] 真机验证：加白名单 → reload → 生物恢复攻击""",
    """快照存在实体上（`@Unique` 字段）而非全局 Map，避免实体卸载后泄漏。
若快照丢失（如实体重新加载），退化为「重建原版 Goal」——需要为每个生物类型
记录其原版 Goal 构造方式，成本高。**优先保证快照不丢**：neutralize 在实体
`finalizeSpawn` 或首次 tick 时执行，快照随实体生命周期存在。""",
    "- 代码：`neutralize/GoalBasedStrategy.java`、`BrainBasedStrategy.java`\n- Commit：`feat(neutralize): 实现可逆还原`")

add("T-NEUT-005", "特殊适配 A 组（袭击系 + 潜影贝 + 幻翼）", "P0", "8h", "agent",
    "T-NEUT-002", "T-NEUT-006, T-NEUT-007",
    "处理 6 个行为特殊的生物：潜影贝、幻翼、掠夺者、卫道士、唤魔者、恼鬼。",
    "- 设计：`02-design.md` §3.5 特殊适配\n- 决策：`02-adr/004`",
    """- [ ] **潜影贝**：移除 `ShulkerAttackGoal`，保持固定方块特性不变
- [ ] **幻翼**：移除 `PhantomAttackPlayerTargetGoal`，不睡眠仍会生成但不攻击
- [ ] **掠夺者/卫道士/唤魔者**：处理共享的 `Raider` 基类，保留袭击事件参与能力
- [ ] **唤魔者**：不再召唤恼鬼攻击玩家
- [ ] **恼鬼**：owner 绑定唤魔者，owner 中立化时恼鬼也中立
- [ ] 袭击（Raid）事件中这些生物**仍会生成**但不主动攻击
- [ ] Johnny 卫道士（自定义名）行为一并处理
- [ ] 逐个真机验证""",
    """⚠️ **风险任务**：三个袭击系生物共享 `Raider` 基类，改动易互相影响。
建议单独开分支 `feat/special-raiders`，逐个验证后合并。

袭击机制的语义问题：袭击本身是「敌对事件」，但生物已中立化。
设计决策：**保留袭击生成，但生物不主动攻击**（村民与铁傀儡仍会攻击它们，
这属于 NPC 互斗，模组不介入）。""",
    "- 代码：`neutralize/special/ShulkerAdapter.java` 等 6 个\n- Commit：分 6 个 commit，每个生物一个",
    "⚠️ 风险任务：`Raider` 基类共享，需单独分支 + 逐个真机验证。")

add("T-NEUT-006", "特殊适配 B 组（凋灵 + 监守者）", "P0", "5h", "agent",
    "T-NEUT-002, T-NEUT-003", "T-NEUT-005, T-NEUT-007",
    "处理两个 Boss/准 Boss：凋灵（硬编码索敌）与监守者（Brain 系 + 振动感知）。",
    "- 设计：`02-design.md` §10 凋灵的处理\n- 决策：`02-adr/004`（凋灵移出默认白名单）",
    """- [ ] **凋灵**：`customServerAiStep()` 内硬编码索敌需 Mixin 拦截
- [ ] 凋灵默认**被中立化**（不在默认白名单）
- [ ] `boss_trading_enabled=false` 时凋灵中立但不开交易界面
- [ ] 凋灵不再主动发射头颅攻击玩家
- [ ] 凋灵召唤时的爆炸/破坏行为保持原版（非攻击行为）
- [ ] **监守者**：Brain 系，禁用振动感知触发的索敌
- [ ] 监守者的 Sonic Boom 不再对玩家释放
- [ ] 监守者默认被中立化（不在默认白名单）
- [ ] 两者真机验证""",
    """**凋灵**的索敌不走标准 `TargetGoal`，在 `WitherBoss#customServerAiStep()` 内硬编码，
必须用 Mixin `@Inject` 拦截，不能靠 `removeAllGoals`。

**监守者**是 Brain 系，但额外有 `VibrationSystem` 接口，
振动感知会触发 `MemoryModuleType.DISTURBANCE_LOCATION` → 索敌。
需同时擦除该 memory。""",
    "- 代码：`neutralize/special/WitherAdapter.java`、`WardenAdapter.java`\n- Commit：`feat(neutralize): 凋灵与监守者特殊适配`")

add("T-NEUT-007", "特殊适配 C 组（末影人 + 僵尸猪灵）", "P0", "5h", "agent",
    "T-NEUT-002", "T-NEUT-005, T-NEUT-006",
    "处理两个原版已实现 `NeutralMob` 的生物，避免原版机制与模组逻辑重叠。",
    "- 验证：`P1-P4-VERIFY.md` P4（本任务由 P4 验证新发现）\n- 决策：`02-adr/004`",
    """- [ ] **末影人**：禁用凝视激怒（`isLookingAtMe` / `setBeingStaredAt`）
- [ ] 玩家看末影人不再触发攻击（凝视属主动索敌，非「受玩家攻击」）
- [ ] 末影人瞬移、搬方块等非攻击行为保持原版
- [ ] **僵尸猪灵**：禁用原版群体报复（`customServerAiStep` 内）
- [ ] 群体报复改由 `KinAlerter` 统一接管（4 格 / 单层 / 禁链式）
- [ ] 验证不出现「双份示警」导致范围失控
- [ ] 两者已实现的 5 个 `NeutralMob` 方法**可复用**，不重复实现存储层
- [ ] 真机验证：攻击一只僵尸猪灵，确认只有 4 格内同类被激怒且不再扩散""",
    """**本任务源于 P4 验证的意外发现** —— 原设计以为猪灵系已实现 `NeutralMob`，
实测是末影人与僵尸猪灵（都是 Goal 系）。

两者均**未调用** `forgetCurrentTargetAndRefreshUniversalAnger()`，
所以「仇恨不扩散到其他玩家」不会被原版破坏，这是好消息。

但**僵尸猪灵的群体报复与 KinAlerter 功能重叠**，必须二选一，
否则一次攻击触发两套传播逻辑，范围会远超 4 格。""",
    "- 代码：`neutralize/special/EndermanAdapter.java`、`ZombifiedPiglinAdapter.java`\n- Commit：`feat(neutralize): 末影人与僵尸猪灵特殊适配`",
    "P4 验证新增任务，原设计文档中不存在。")

for t in T:
    (OUT / f"{t['tid']}.md").write_text(TPL.format(**t), encoding="utf-8")

print(f"已生成 {len(T)} 个任务文件 -> {OUT}")
for t in T:
    print(f"  {t['tid']}.md")
