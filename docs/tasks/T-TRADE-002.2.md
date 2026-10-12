- [ ] T-TRADE-002.2: 运行时报价单组装器（遍历定价表+门控）

**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-TRADE-002.1、T-PRICE-003（PriceTable）
**可并行：** T-NEUT-002

## 目标

为一只可交易生物，遍历其定价表组装整份 MerchantOffers；门控不通过返回空列表。

## 来源

- 拆分自：T-TRADE-002

## 验收标准

- [ ] 遍历该生物定价表，逐条 TradeSpec.toOffer() 组成 MerchantOffers
- [ ] 白名单内 / 未适配 / canTrade=false（含 boss_trading_enabled=false 的 Boss）返回空列表
- [ ] 报价查询 O(1)~O(掉落物种类)，结果在构表期缓存
- [ ] 组装出的报价供 MobMerchantMixin.getOffers 接入（与右键交易链 T-TRADE-003 联调）

## 技术要点

- 原规划类名 TradeOfferBuilder；落地为 PricingEngine/PriceTable 之上的组装器，命名实现时定

## 产出物

- 代码：trade 报价组装器
- 测试：组装/门控空单单测
- Commit：待提交

## 备注

无
