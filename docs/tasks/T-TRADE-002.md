- [-] T-TRADE-002: TradeOfferBuilder 构建交易列表

**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-PRICE-003, T-TRADE-001
**可并行：** T-NEUT-002

## 目标

根据生物类型与定价表构建 `MerchantOffers`，每个掉落物一条交易。

## 来源

- 设计：`../02-design.md` §3.4 交易规格

## 子任务（状态由子任务聚合，勿手改本卡状态）

- [x] T-TRADE-002.1: TradeSpec 单条报价纯逻辑（L1）
- [ ] T-TRADE-002.2: 运行时报价单组装器（遍历定价表+门控）

## 技术要点

`MerchantOffer(ItemCost baseCostA, Optional<ItemCost> costB, ItemStack result, int maxUses, int xp, float priceMultiplier)`

1.21.1 用 `ItemCost` 而非旧版 `ItemStack`。
价格上限 128 正是因为双槽 64+64。

## 产出物

- 代码：`trade/TradeOfferBuilder.java`
- 测试：`TradeOfferBuilderTest.java`
- Commit：`feat(trade): 实现交易列表构建`

## 备注

无
