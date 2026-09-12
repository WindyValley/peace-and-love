# T-TRADE-002: TradeOfferBuilder 构建交易列表

**状态：** todo
**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-PRICE-003, T-TRADE-001
**可并行：** T-NEUT-002

## 目标

根据生物类型与定价表构建 `MerchantOffers`，每个掉落物一条交易。

## 来源

- 设计：`../02-design.md` §3.4 交易规格

## 验收标准

- [ ] 输入槽为绿宝石，数量 = 定价表价格
- [ ] 价格 > 64 时拆分为两槽（如 117 = 64 + 53）
- [ ] 输出槽为掉落物，数量按设计取值
- [ ] `maxUses = 1`（每日 1 次）
- [ ] `xp = 0`（不给经验，非村民）
- [ ] 白名单内或未适配生物返回空列表

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
