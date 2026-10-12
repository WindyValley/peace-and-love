# Peace And Love — 详细设计

- 版本：v1.0
- 日期：2026-09-11
- 依据：`01-requirements.md` v0.3、`02-tech-stack.md` v1.0、`adr/` 001~004
- MC 版本：1.21.1 ｜ Java 21 ｜ Mod ID `peaceandlove` ｜ 包名 `top.windyvalley.peaceandlove`

> **所有 MC 内部 API 签名均来自 1.21.1 官方 server.jar + 官方 mappings 实测**（见 `spikes/design-verify/`）

---

## 1. 工程结构

```
peace-and-love/
├── build.gradle                    # Architectury Loom 根配置
├── gradle.properties               # 版本号集中管理
├── settings.gradle
├── common/                         # ~85% 代码
│   └── src/main/
│       ├── java/top/windyvalley/peaceandlove/
│       │   ├── PeaceAndLove.java              # 公共入口
│       │   ├── config/
│       │   │   ├── ModConfig.java             # 配置数据类
│       │   │   └── ConfigManager.java         # 加载 / 热重载
│       │   ├── registry/
│       │   │   └── AdaptedMobRegistry.java    # 已适配列表（代码常量）
│       │   ├── scope/
│       │   │   └── NeutralizationScope.java   # 生效判定
│       │   ├── pricing/
│       │   │   ├── PricingEngine.java         # 对数曲线
│       │   │   ├── LootPriceProvider.java     # 战利品表解析（接口）
│       │   │   ├── LootPriceProviderImpl.java
│       │   │   ├── TradeSpec.java             # 单条交易规格
│       │   │   └── PriceCache.java
│       │   ├── trade/
│       │   │   ├── TradeOfferBuilder.java
│       │   │   └── RestockManager.java
│       │   ├── anger/
│       │   │   ├── AngerController.java
│       │   │   ├── AngerSource.java           # enum
│       │   │   └── KinAlerter.java
│       │   └── strategy/
│       │       ├── NeutralizationStrategy.java
│       │       ├── GoalBasedStrategy.java
│       │       ├── BrainBasedStrategy.java
│       │       ├── GoalSnapshot.java          # 支持 restore()
│       │       └── special/                   # 10 个特殊适配
│       │           ├── ShulkerAdapter.java
│       │           ├── PhantomAdapter.java
│       │           ├── RaiderAdapter.java     # 掠夺者/卫道士/唤魔者
│       │           ├── VexAdapter.java
│       │           ├── WitherAdapter.java
│       │           ├── WardenAdapter.java
│       │           ├── EndermanAdapter.java   # P4 新增：禁用凝视激怒
│       │           └── ZombifiedPiglinAdapter.java  # P4 新增：接管群体报复
│       └── resources/
│           └── peaceandlove.mixins.json
│           └── mixin/
│               ├── MobMerchantMixin.java      # implements Merchant
│               ├── LivingEntityHurtMixin.java # 仇恨触发
│               └── LootTableAccessor.java     # ×7 @Accessor
├── fabric/
└── neoforge/
    └── src/main/resources/META-INF/
        └── accesstransformer.cfg              # P1 待验证是否需要
```

---

## 2. 分层与依赖规则

| 层 | 内容 | 依赖 |
|----|------|------|
| **L1 基础设施** | `ConfigManager` `AdaptedMobRegistry` `NeutralizationScope` `PricingEngine` `LootPriceProvider` | 不依赖上层，**可独立单测** |
| **L2 领域逻辑** | `AngerController` `TradeOfferBuilder` `RestockManager` `NeutralizationStrategy` | 只依赖 L1 |
| **L3 Mixin** | `MobMerchantMixin` `LivingEntityHurtMixin` `LootTableAccessor` | **唯一接触 MC 内部实现的层**，版本适配集中于此 |
| **L4 平台入口** | `FabricInitializer` `NeoForgeInitializer` | 尽量薄 |

---

## 3. 核心接口设计

### 3.1 生效范围判定

```java
public final class NeutralizationScope {
    /**
     * 生效判定 = 在已适配列表 AND 不在白名单
     * 见 ADR-004 决策一
     */
    public static boolean isNeutralized(EntityType<?> type) {
        return AdaptedMobRegistry.isAdapted(type)
            && !ConfigManager.get().hostileWhitelist.contains(type);
    }

    /** 是否生成交易 offer（Boss 需额外开关） */
    public static boolean canTrade(EntityType<?> type) {
        if (!isNeutralized(type)) return false;
        if (AdaptedMobRegistry.isBoss(type)) {
            return ConfigManager.get().bossTradingEnabled;   // 默认 false
        }
        return true;
    }
}
```

### 3.2 已适配生物列表（代码常量）

```java
public final class AdaptedMobRegistry {

    /** Goal 系 32 个 —— removeAllGoals(Predicate) 移除主动索敌 */
    public static final Set<EntityType<?>> GOAL_BASED = Set.of(
        EntityType.BLAZE,              // 烈焰人
        EntityType.BOGGED,             // 沼骸
        EntityType.CAVE_SPIDER,        // 洞穴蜘蛛
        EntityType.CREEPER,            // 苦力怕
        EntityType.DROWNED,            // 溺尸
        EntityType.ELDER_GUARDIAN,     // 远古守卫者
        EntityType.ENDERMAN,           // 末影人
        EntityType.ENDERMITE,          // 末影螨
        EntityType.EVOKER,             // 唤魔者      🔒默认白名单 ⚠️特殊
        EntityType.GHAST,              // 恶魂
        EntityType.GIANT,              // 巨人
        EntityType.GUARDIAN,           // 守卫者
        EntityType.HUSK,               // 尸壳
        EntityType.ILLUSIONER,         // 幻术师
        EntityType.MAGMA_CUBE,         // 岩浆怪
        EntityType.PHANTOM,            // 幻翼        🔒默认白名单 ⚠️特殊
        EntityType.PILLAGER,           // 掠夺者      🔒默认白名单 ⚠️特殊
        EntityType.RAVAGER,            // 劫掠兽
        EntityType.SHULKER,            // 潜影贝      🔒默认白名单 ⚠️特殊
        EntityType.SILVERFISH,         // 蠹虫
        EntityType.SKELETON,           // 骷髅
        EntityType.SLIME,              // 史莱姆
        EntityType.SPIDER,             // 蜘蛛
        EntityType.STRAY,              // 流浪者
        EntityType.VEX,                // 恼鬼        🔒默认白名单 ⚠️特殊
        EntityType.VINDICATOR,         // 卫道士      🔒默认白名单 ⚠️特殊
        EntityType.WITCH,              // 女巫
        EntityType.WITHER,             // 凋灵        ⚠️特殊适配（默认中立化）
        EntityType.WITHER_SKELETON,    // 凋灵骷髅
        EntityType.ZOMBIE,             // 僵尸
        EntityType.ZOMBIE_VILLAGER,    // 僵尸村民
        EntityType.ZOMBIFIED_PIGLIN    // 僵尸猪灵
    );

    /** Brain 系 6 个 —— 擦除 ANGRY_AT / ATTACK_TARGET 记忆 */
    public static final Set<EntityType<?>> BRAIN_BASED = Set.of(
        EntityType.BREEZE,             // 旋风人
        EntityType.HOGLIN,             // 疣猪兽      ⚠️已实现 NeutralMob
        EntityType.PIGLIN,             // 猪灵        ⚠️已实现 NeutralMob
        EntityType.PIGLIN_BRUTE,       // 猪灵蛮兵    ⚠️已实现 NeutralMob
        EntityType.WARDEN,             // 监守者      ⚠️特殊
        EntityType.ZOGLIN               // 僵尸疣猪兽  ⚠️已实现 NeutralMob
    );

    /** ⏸ v1.0 暂缓：末影龙（自有 Phase AI），不进已适配列表也不进白名单 */
    public static final Set<EntityType<?>> DEFERRED = Set.of(
        EntityType.ENDER_DRAGON
    );

    public static boolean isAdapted(EntityType<?> t) {
        return GOAL_BASED.contains(t) || BRAIN_BASED.contains(t);
    }
}
```

### 3.3 定价引擎

```java
public final class PricingEngine {
    /**
     * 对数曲线定价（ADR-003）
     * pos   = log(cheap/epk) / log(cheap/rare)
     * price = clamp(1 + (MAX-1) × pos, 1, MAX)
     */
    public static int price(double epk, double cheap, double rare, int max) {
        if (epk <= 0)     return max;
        if (epk >= cheap) return 1;
        if (epk <= rare)  return max;
        double pos = Math.log(cheap / epk) / Math.log(cheap / rare);
        return Mth.clamp((int) Math.round(1 + (max - 1) * pos), 1, max);
    }
}
```

### 3.4 交易规格

```java
public record TradeSpec(
    Item     item,          // 掉落物
    int      count,         // 单次产出 = 原版一次击杀最大掉落量
    int      price,         // 绿宝石价格 [1, PRICE_MAX]
    double   epk            // 期望每次击杀产出（调试与 /pal debug 用）
) {
    /** 价格 > 64 时拆成两个输入槽（ADR-003） */
    public MerchantOffer toOffer() {
        ItemCost costA = new ItemCost(Items.EMERALD, Math.min(price, 64));
        Optional<ItemCost> costB = price > 64
            ? Optional.of(new ItemCost(Items.EMERALD, price - 64))
            : Optional.empty();
        return new MerchantOffer(
            costA, costB,
            new ItemStack(item, count),
            /* uses            */ 0,
            /* maxUses         */ 1,          // ★ 每日 1 次
            /* rewardExp       */ false,
            /* priceMultiplier */ 0.0F        // ★ 禁用需求量价格漂移
        );
    }
}
```

### 3.5 中立化策略

```java
public interface NeutralizationStrategy {
    boolean supports(EntityType<?> type);
    void neutralize(Mob mob);
    void restore(Mob mob);        // 白名单热重载时恢复原版行为
}
```

**Goal 系实现要点：**

```java
public class GoalBasedStrategy implements NeutralizationStrategy {

    @Override
    public void neutralize(Mob mob) {
        // 1. 快照，供 restore() 使用（WrappedGoal 的 getGoal/getPriority 均为 public）
        GoalSnapshot.capture(mob);

        // 2. 移除主动索敌 Goal，保留 HurtByTargetGoal
        //    实测确认 GoalSelector 有 removeAllGoals(Predicate)，无需反射
        ((MobAccessor) mob).getTargetSelector().removeAllGoals(
            goal -> goal instanceof NearestAttackableTargetGoal<?>
                 || goal instanceof TargetGoal && !(goal instanceof HurtByTargetGoal)
        );
    }

    @Override
    public void restore(Mob mob) {
        GoalSnapshot.restore(mob);   // 原样重建 (priority, goal) 对
    }
}
```

**Brain 系实现要点：**

```java
public class BrainBasedStrategy implements NeutralizationStrategy {

    @Override
    public void neutralize(Mob mob) {
        Brain<?> brain = mob.getBrain();
        brain.eraseMemory(MemoryModuleType.ANGRY_AT);
        brain.eraseMemory(MemoryModuleType.ATTACK_TARGET);
        // 每 tick 拦截索敌 Behavior（见 §5.2）
    }
}
```

### 3.6 仇恨控制

```java
public enum AngerSource {
    NONE,            // 中立，可交易
    PLAYER_DIRECT,   // 被玩家直接攻击 —— 唯一的主动触发源
    KIN_ALERT        // 同族示警（不再向外传播）
}

public final class AngerController {

    /** 唯一入口：仅玩家攻击触发（ADR-004 决策三） */
    public static void onPlayerAttack(Mob mob, Player attacker) {
        if (!NeutralizationScope.isNeutralized(mob.getType())) return;

        mob.setTarget(attacker);
        ((NeutralMob) mob).setPersistentAngerTarget(attacker.getUUID());
        ((NeutralMob) mob).startPersistentAngerTimer();
        setAngerSource(mob, AngerSource.PLAYER_DIRECT);

        KinAlerter.alert(mob, attacker);
    }

    /**
     * ⚠️ 禁止调用 forgetCurrentTargetAndRefreshUniversalAnger()
     *    它有 "universal anger"（对所有玩家记仇）语义，
     *    违反「仇恨不扩散到其他玩家」的需求
     */
    public static void calmDown(Mob mob) {
        ((NeutralMob) mob).stopBeingAngry();
        mob.setTarget(null);
        setAngerSource(mob, AngerSource.NONE);
    }
}
```

```java
public final class KinAlerter {
    /** 单层示警，严格同 EntityType，不链式传播 */
    public static void alert(Mob source, Player attacker) {
        double r = ConfigManager.get().kinAlertRadius;   // 默认 4.0
        AABB box = source.getBoundingBox().inflate(r);

        source.level().getEntitiesOfClass(Mob.class, box,
            m -> m != source
              && m.getType() == source.getType()               // ★ 严格同类
              && m.distanceToSqr(source) <= r * r              // ★ 球形而非立方体
              && NeutralizationScope.isNeutralized(m.getType())
        ).forEach(kin -> {
            kin.setTarget(attacker);
            ((NeutralMob) kin).setPersistentAngerTarget(attacker.getUUID());
            ((NeutralMob) kin).startPersistentAngerTimer();
            setAngerSource(kin, AngerSource.KIN_ALERT);       // ★ 不再向外示警
        });
    }
}
```

---

## 4. Mixin 设计

### 4.1 `MobMerchantMixin` —— 注入交易能力

```java
@Mixin(Mob.class)
public abstract class MobMerchantMixin implements Merchant {

    @Unique private Player          pal$tradingPlayer;
    @Unique private MerchantOffers  pal$offers;
    @Unique private long            pal$lastRestockDay = -1;

    // ── Merchant 的 10 个 abstract 方法 ──
    @Override public void setTradingPlayer(Player p)      { pal$tradingPlayer = p; }
    @Override public Player getTradingPlayer()            { return pal$tradingPlayer; }
    @Override public void overrideOffers(MerchantOffers o){ pal$offers = o; }
    @Override public void notifyTrade(MerchantOffer offer){ offer.increaseUses(); }
    @Override public void notifyTradeUpdated(ItemStack s) { /* 音效等 */ }
    @Override public int  getVillagerXp()                 { return 0; }
    @Override public void overrideXp(int xp)              { }
    @Override public boolean showProgressBar()            { return false; }
    @Override public SoundEvent getNotifyTradeSound()     { return SoundEvents.VILLAGER_YES; }
    @Override public boolean isClientSide()               { return level().isClientSide; }
    // canRestock() 与 openTradingScreen() 有 default 实现，无需覆写

    @Override
    public MerchantOffers getOffers() {
        Mob self = (Mob)(Object) this;
        if (self.level().isClientSide) return pal$offers == null ? pal$EMPTY : pal$offers;
        if (!NeutralizationScope.canTrade(self.getType(), cfg)) return pal$EMPTY;  // 零分配
        PriceTable table = PeaceAndLove.priceTable().table();
        // 定价表 reload 后实例身份变化 → 已存在生物也懒重建（uses 归零，补货落地前接受）
        if (pal$offers == null || pal$offersTable != table) {
            pal$offers = TradeOfferBuilder.assemble(self.getType(), cfg, table);
            pal$offersTable = table;
        }
        return pal$offers;   // RestockManager.tick（T-TRADE-004）每日补货，后续接入
    }

    /**
     * 右键交互 → 打开原版交易 GUI（T-TRADE-003，已真机验证）。
     *
     * 关键：服务端权威，客户端【完全不干预】。客户端物理端没有服务端配置 /
     * 仇恨 / 报价（Brain 记忆不与客户端同步），在客户端猜门控会对村民等未适配
     * 实体产生错误 SUCCESS 预测；开界面完全由服务端 openTradingScreen 的
     * openMenu + ClientboundMerchantOffersPacket 驱动，天然支持客户端不装 mod
     * （P2 已真机验证：零 PAL 类客户端照常交易，见 P1-P4-VERIFY §P2）。
     *
     * 门控真值表抽到纯函数 TradeInteraction.evaluate 单测覆盖，这里只抽取事实。
     */
    @Inject(method = "mobInteract", at = @At("HEAD"), cancellable = true)
    private void pal$onMobInteract(Player player, InteractionHand hand,
                                   CallbackInfoReturnable<InteractionResult> cir) {
        Mob self = (Mob)(Object) this;
        if (self.level().isClientSide) return;                 // 客户端放行原版 PASS

        boolean bothHandsEmpty =
                player.getItemInHand(MAIN_HAND).isEmpty()
             && player.getItemInHand(OFF_HAND).isEmpty();
        Decision d = TradeInteraction.evaluate(
                NeutralizationScope.canTrade(self.getType(), cfg),  // 适配+白名单+开关+boss
                AngerController.isAngry(self),                    // 三路仇恨，见 §4.2/AngerController
                self.isAlive(),
                getTradingPlayer() == null,                       // 防 interactAt+interact 重复开窗
                bothHandsEmpty,                                   // 持物保留原版交互
                !getOffers().isEmpty());                          // 空报价=没货
        if (d == FALL_THROUGH) return;                           // 不注入，保持原版
        if (hand == MAIN_HAND && d == OPEN) {
            setTradingPlayer(player);
            openTradingScreen(player, self.getDisplayName(), 0); // ★ 原版 default 实现
        }
        cir.setReturnValue(InteractionResult.CONSUME);           // OPEN 与 EMPTY_OFFERS 都吞交互
    }

    /** NBT 持久化：只需存 lastRestockDay，offers 由原版 CODEC 覆盖 */
    @Inject(method = "addAdditionalSaveData", at = @At("TAIL"))
    private void pal$save(CompoundTag tag, CallbackInfo ci) {
        tag.putLong("pal_lastRestockDay", pal$lastRestockDay);
        if (pal$offers != null) tag.put("pal_offers", pal$offers.createTag());
    }
}
```

### 4.2 `LivingEntityHurtMixin` —— 仇恨触发点

```java
@Mixin(LivingEntity.class)
public abstract class LivingEntityHurtMixin {

    /**
     * 实测签名：boolean hurt(DamageSource, float)
     * 注入 HEAD 并尽早返回，降低高频调用开销
     */
    @Inject(method = "hurt", at = @At("HEAD"))
    private void pal$onHurt(DamageSource source, float amount, CallbackInfoReturnable<Boolean> cir) {
        Object self = this;
        if (!(self instanceof Mob mob)) return;

        // 快速路径：不在适配范围直接返回
        if (!NeutralizationScope.isNeutralized(mob.getType())) return;

        // ★ 唯一触发条件：攻击者是玩家
        //   getEntity() 已自动解析投射物 owner（射箭的玩家）
        if (source.getEntity() instanceof Player player) {
            AngerController.onPlayerAttack(mob, player);
        }
        // NPC 攻击 / 环境伤害 → 不介入，走原版逻辑
    }
}
```

### 4.3 `LootTableAccessor` —— 战利品表解析

`LootTable` 在 1.21.1 是 **record**，`pools()` 有 public accessor，结构遍历零 Mixin。仅需 7 个 `@Accessor` 读取内部字段（`LootPool.entries` / `conditions` / `functions` 等），单文件 ≤ 60 行。

---

## 5. 关键数据流

### 5.1 启动时构建定价表

```
ModInitializer
  → ConfigManager.load()
  → 等待数据包加载完成（战利品表可能被数据包覆盖）
  → LootPriceProvider.buildPriceTable(AdaptedMobRegistry.all())
      for 每个已适配生物:
        table.pools()                       // record accessor
        → @Accessor 读 entries/conditions/functions
        → 计算 epk（基准：玩家击杀 + looting 0）
        → PricingEngine.price(epk, cheap, rare, PRICE_MAX)
  → PriceCache.put(EntityType → List<TradeSpec>)
```

运行期只读缓存，**零反射开销**。

### 5.2 Brain 系每 tick 拦截

Goal 系是"移除一次即永久生效"，Brain 系不同 —— `Brain.tick()` 会重新评估记忆，因此需要每 tick 擦除：

```java
// 在 Mob.tick() 的 TAIL 注入（仅 Brain 系生物）
if (NeutralizationScope.isNeutralized(type) && !AngerController.isAngry(mob)) {
    brain.eraseMemory(MemoryModuleType.ANGRY_AT);
    brain.eraseMemory(MemoryModuleType.ATTACK_TARGET);
}
```

> ⚠️ 性能：仅对 6 个 Brain 系生物执行，且有 `isNeutralized` 快速判定，开销可接受。dev 阶段需实测。

### 5.3 每日补货

```java
public final class RestockManager {
    public static void tick(Mob mob, MerchantOffers offers) {
        long today = mob.level().getDayTime() / 24000L;
        long last  = getLastRestockDay(mob);
        int  period = ConfigManager.get().restockIntervalDays;   // 默认 1

        if (last < 0 || today - last >= period) {
            // ⚠️ 不能调用 Villager.restock() —— 它耦合 gossip/demand/价格波动
            offers.forEach(MerchantOffer::resetUses);
            setLastRestockDay(mob, today);
        }
    }
}
```

---

## 6. 配置文件设计

```json5
{
  // ── 生效范围 ──
  "hostile_whitelist": [                  // 已适配但保持原版行为
    "minecraft:pillager",
    "minecraft:vindicator",
    "minecraft:evoker",
    "minecraft:vex",
    "minecraft:phantom",
    "minecraft:shulker"
  ],

  // ── 仇恨 ──
  "kin_alert_radius": 4.0,                // 同族示警半径（球形），仅玩家攻击触发
  "anger_cooldown_seconds": 30,           // 0 = 永久敌对
  "anger_cooldown_distance": 32.0,

  // ── 交易 ──
  "trading_enabled": true,
  "boss_trading_enabled": false,          // Boss 中立化但不开交易
  "max_uses_per_day": 1,                  // MerchantOffer.maxUses
  "restock_interval_days": 1,             // 1=每天，3=三天一次

  // ── 定价 ──
  "price_max": 128,                       // 上限（MerchantOffer 双槽 64+64）
  "epk_cheap": 2.0,                       // 廉价锚点
  "epk_rare": 0.005,                      // 稀有锚点
  "price_overrides": {                    // 手工修正（可选）
    // "minecraft:zombie/minecraft:iron_ingot": 100
  }
}
```

---

## 7. 命令设计

主命令 `/pal`（简写）与 `/peaceandlove`（完整名）**同时注册**，对用户更友好。两者等价。

| 命令 | 权限 | 作用 |
|------|------|------|
| `/pal reload` | OP 2 | 热重载配置，触发 `restore()` + 重新 `neutralize()` |
| `/pal whitelist list` | OP 2 | 列出当前白名单（未适配条目标注「无效」） |
| `/pal whitelist add <id>` | OP 2 | 加入白名单。tab 补全来自**已适配列表**（排除已在白名单的），支持带/不带 `minecraft:` 前缀 |
| `/pal whitelist remove <id>` | OP 2 | 移出白名单。tab 补全来自当前白名单 |
| `/pal debug price <entity>` | OP 2 | 打印该生物的完整定价表（epk / 价格 / 产出） |
| `/pal debug scope <entity>` | OP 2 | 打印生效判定过程（是否适配 / 是否白名单 / 结论） |
| `/pal debug anger` | OP 2 | 打印附近生物的仇恨状态与来源 |

> **实现说明**：命令层只做参数解析与消息回显，所有逻辑委托给 `ConfigManager`（已单测覆盖）。基于 Architectury `CommandRegistrationEvent`，common 模块一处注册、Fabric/NeoForge 两端生效。
>
> **验证方式**：命令注册、权限、tab 补全依赖服务端运行时，无法用纯 JUnit 验证，属「已写未验」，待 T-NEUT 挂上 Mixin、服务端可启动后真机验证。

---

## 8. 测试设计

### 8.1 单元测试（L1/L2，不依赖 MC 运行时）

| 测试类 | 覆盖 |
|--------|------|
| `PricingEngineTest` | 对数曲线单调性（110 条数据）、边界 clamp、锚点行为 |
| `NeutralizationScopeTest` | 已适配 ∩ 白名单 的四象限组合 |
| `RestockLogicTest` | 跨日判定、周期配置、首次补货 |
| `TradeSpecTest` | 价格 > 64 时的双槽拆分正确性 |

### 8.2 真机验证清单（必须装 APK/服务端实测）

> 用户偏好：单测全绿不够，涉及渲染/时序的必须真机验证

| # | 场景 | 验证点 |
|---|------|--------|
| 1 | 右键中立僵尸 | 交易界面正常打开，价格与 `final_pricing_128.json` 一致 |
| 2 | 交易腐肉 | 扣 16 绿宝石得 2 腐肉，该条目变为售罄 |
| 3 | 等待一游戏日 | 售罄条目恢复可交易 |
| 4 | 玩家攻击僵尸 | 转敌对，追击**该玩家** |
| 5 | 4 格内同族 | 被示警转敌对；6 格外保持中立 |
| 6 | 被示警的个体 | **不再**向更外层传播 |
| 7 | 铁傀儡攻击僵尸 | 模组**不介入**，走原版逻辑，不示警 |
| 8 | **多人：A 交易时 B 攻击** | 怪物追 **B 不追 A**；A 的界面关闭，绿宝石退回 |
| 9 | 脱战 30 秒 | 恢复中立，可再次交易 |
| 10 | 白名单热重载 | 移出掠夺者 → 立即中立化；加回 → 恢复原版行为 |
| 11 | 装第三方怪物 Mod | 其生物**完全不受影响** |
| 12 | 客户端不装模组 | ✅ 能正常交易（P2 已真机验证 2026-10-12，见 P1-P4-VERIFY §P2） |

---

## 9. 待验证项（dev 阶段前置）

| # | 验证项 | 关联 | 影响 |
|---|--------|------|------|
| **P1** | NeoForge Mixin 接口注入是否需要 Access Transformer | ADR-002 | 需额外维护 `accesstransformer.cfg` |
| **P2** | 客户端不装模组能否交易 | ADR-002 | 若能则是重要卖点 |
| **P3** | 注入 `Mob` 基类 vs 38 个目标类 | ADR-002 | 影响面 vs 代码量 |
| **P4** | 猪灵/疣猪兽已实现的 `NeutralMob` 是否冲突 | ADR-004 | 涉及 4 个生物 |

---

## 10. 凋灵的处理（已决策）

**决策（用户 2026-09-11）：凋灵移出默认白名单，默认被中立化。**

### 背景

凋灵在 R3 v3 修正中经字节码复核，确认为**标准 Goal 系**（引用 `goalSelector`/`targetSelector`，覆写 `registerGoals()`），先前"Boss 专属弹幕 AI"的说法是误判。归类修正后它一度被放入默认白名单，与先前"默认白名单 6 项"的口径不符，故提请确认。

### 最终配置

```
默认白名单（6 项）：掠夺者、卫道士、唤魔者、恼鬼、幻翼、潜影贝
凋灵：已适配，不在默认白名单 → 默认中立化
末影龙：不适配、不在白名单 → 行为完全不变（v1.1 再议）
```

### 实际效果

| 生物 | 中立化 | 交易 | 说明 |
|------|--------|------|------|
| 凋灵 | ✅ 默认生效 | ❌ 默认关闭 | `boss_trading_enabled=false` 时只中立化不开交易 |
| 监守者 | ✅ 默认生效 | ✅ | 与凋灵同等对待原则 |
| 末影龙 | ❌ 不适配 | ❌ | 配置无效，日志给 INFO 提示 |

凋灵被中立化后**不会主动攻击玩家**，但玩家攻击它仍会反击（`HurtByTargetGoal` 保留）。管理员若要恢复原版凋灵战，将 `minecraft:wither` 加入白名单即可。

> ⚠️ 需注意：凋灵的 target 选择在 `customServerAiStep` 中另有硬编码，属 8 个特殊适配之一，`WitherAdapter` 需覆盖该路径。

---

## 变更记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-09-11 | v1.0 | 首版。工程结构、四层架构、核心接口、Mixin 设计、数据流、配置、命令、测试清单 |
