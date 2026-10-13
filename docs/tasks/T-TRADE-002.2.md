- [x] T-TRADE-002.2: 运行时报价单组装器（遍历定价表+门控）

**完成备注：** 2026-10-13 回填：getOffers 已由 MobMerchantMixin 懒组装接入（c195627），003/004/005 双端真机联调全绿
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

- [x] 遍历该生物定价表，逐条 TradeSpec.toOffer() 组成 MerchantOffers
- [x] 白名单内 / 未适配 / canTrade=false（含 boss_trading_enabled=false 的 Boss）返回空列表
- [x] 价格在构表期算好缓存（PriceTable，O(1) 取列表）；组装本身 O(掉落物种类)，报价单由 MobMerchantMixin 首次 getOffers 懒组装并按怪物缓存（pal$offers，持有各自 uses）
- [x] 组装出的报价供 MobMerchantMixin.getOffers 接入（代码已接 c195627；mixin 织入后游戏内取价/显示与右键交易链 T-TRADE-003 一并真机联调）

## 技术要点

- 落地类名 TradeOfferBuilder（对齐设计 §4.1）。纯薄转换层：门控 canTrade + 遍历 PriceTable.offersFor + TradeSpec.toOffer，不重复定价。每次返回新容器/新 offer（uses 按怪物隔离）；每只怪物的报价单由 MobMerchantMixin.pal$offers 懒缓存。

## 产出物

- 代码：`trade/TradeOfferBuilder.java`（assemble 组装器）、`mixin/MobMerchantMixin.java`（getOffers 接入）
- 测试：`trade/TradeOfferBuilderTest.java`（7：组装/白名单/未适配/trading关/Boss开关正反/无掉落空单/实例隔离）；common 165 绿
- Commit：c195627

## 备注

- 验收 4（mixin 织入后游戏内取价/显示）待 T-TRADE-003 右键交易链接入后真机联调；组装/门控逻辑本身已由单测锁定。
