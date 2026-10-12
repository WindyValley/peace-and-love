- [x] T-TRADE-002.1: TradeSpec 单条报价纯逻辑（L1）

**完成备注：** TradeSpec 纯逻辑已落地（commit 1bd7bcc），TradeSpecTest 覆盖双槽/maxUses/xp/上限；运行时组装在 .2
**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-PRICE-002.1（PricingEngine 定价）
**可并行：** T-NEUT-002

## 目标

把一条掉落物定价结果转成原版 MerchantOffer 的纯逻辑：绿宝石双槽、限购、零经验零漂移。

## 来源

- 拆分自：T-TRADE-002

## 验收标准

- [x] 输入槽为绿宝石，数量 = 定价表价格
- [x] 价格 > 64 拆分为两槽（如 117 = 64 + 53）
- [x] 输出槽为掉落物，数量 = count（looting 0 上界）
- [x] maxUses = 1（每个补货周期每样一次）
- [x] xp = 0、priceMultiplier = 0（非村民，不升级、不漂移）
- [x] price > 128 抛 IllegalArgumentException（双槽 64+64 硬上限）

## 技术要点

- 纯 record + toOffer()，零 MC 服务依赖，TradeSpecTest 纯 JUnit 覆盖

## 产出物

- 代码：trade/TradeSpec.java
- 测试：trade/TradeSpecTest.java
- Commit：1bd7bcc

## 备注

L1 纯逻辑已落地（commit 1bd7bcc）；运行时整单组装见 .2
