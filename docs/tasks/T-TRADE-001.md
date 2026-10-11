- [x] T-TRADE-001: MobMerchantMixin 注入 Merchant 接口

**完成备注：** 单测/编译；双端运行时待 T-TRADE-002 有真实报价后一并真机验证，方法集与 P1 探针一致，探针已双端验证
**优先级：** P0
**预估：** 5h
**Owner：** agent
**依赖：** T-SCOPE-002
**可并行：** T-NEUT-001

## 目标

通过 Mixin 向 `Mob` 基类注入 `Merchant` 接口，实现全部 10 个 abstract 方法。

## 来源

- 设计：`../02-design.md` §4.1
- 决策：`../adr/002`
- 验证：`../P1-P4-VERIFY.md` P1

## 验收标准

- [ ] `@Mixin(Mob.class) implements Merchant` 编译通过
- [ ] 实现 10 个 abstract 方法（见技术要点）
- [ ] `@Unique` 字段前缀 `pal$`
- [ ] `getOffers()` 懒加载，非目标生物永远返回空
- [ ] **双端**运行时 `Merchant.isAssignableFrom(Mob.class) == true`
- [ ] 不需要 Access Transformer（accesswidener 保持空）

## 技术要点

**`Merchant` 共 12 个方法 = 10 abstract + 2 default**（字节码实测，勿凭印象）：

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

字段（3 个）：`pal$tradingPlayer` / `pal$offers` / `pal$lastRestockDay`。

## 产出物

- 代码：`mixin/MobMerchantMixin.java`
- Commit：`feat(trade): Mixin 注入 Merchant 接口`

## 备注

P1 已在真实 NeoForge 服务端验证注入成功，本任务是把探针代码正式化。
