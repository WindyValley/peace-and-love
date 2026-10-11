- [ ] T-TRADE-003: 右键交互打开交易界面

**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-TRADE-001
**可并行：** T-TRADE-004

## 目标

玩家右键中立化生物时打开交易 GUI，复用原版 `openTradingScreen`。

## 来源

- 设计：`../02-design.md` §3.4
- 需求：FR-2.2

## 验收标准

- [ ] 右键中立化生物打开交易界面
- [ ] 白名单内/未适配生物右键无反应（保持原版行为）
- [ ] `trading_enabled=false` 时不开界面
- [ ] Boss 且 `boss_trading_enabled=false` 时不开界面
- [ ] 处于仇恨状态的生物不开界面
- [ ] 空手右键才触发，持物品时不拦截原版交互

## 技术要点

在 `Mob#mobInteract` 注入，返回 `InteractionResult.sudo`。
**服务端权威**：`if (level().isClientSide) return InteractionResult.SUCCESS;`

直接调 `openTradingScreen(player, getDisplayName(), 0)`，
这是 default 方法，内部走原版 `MerchantMenu` + `ClientboundMerchantOffersPacket`。

## 产出物

- 代码：`mixin/MobMerchantMixin.java`
- Commit：`feat(trade): 实现右键打开交易界面`

## 备注

无
