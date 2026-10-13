- [x] T-TRADE-003: 右键交互打开交易界面

**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-TRADE-001
**可并行：** T-TRADE-004
**状态：** ✅ done（2026-10-12，common 单测 173 全绿 + 真机 8/8 PASS）

## 目标

玩家右键中立化生物时打开交易 GUI，复用原版 `openTradingScreen`。

## 来源

- 设计：`../02-design.md` §3.4 / §4.1
- 需求：FR-2.2

## 验收标准

- [x] 右键中立化生物打开交易界面（真机：僵尸 MerchantScreen 4 条报价）
- [x] 白名单内/未适配生物右键无反应（真机：白名单僵尸 + 未适配牛均不开，保持原版）
- [x] `trading_enabled=false` 时不开界面（真机）
- [x] Boss 且 `boss_trading_enabled=false` 时不开界面（真机：自然召唤监守者，关不开/开则 1 条报价）
- [x] 处于仇恨状态的生物不开界面（真机：攻击后 anger=PLAYER_DIRECT 不开）
- [x] 空手右键才触发，持物品时不拦截原版交互（真机：主手持物不开）

## 技术要点（实现与任务卡初版的差异，以真机为准）

- 门控抽纯函数 `trade/TradeInteraction.evaluate`（三态 OPEN / EMPTY_OFFERS / FALL_THROUGH），Mixin 只抽事实。
- **客户端不 `return SUCCESS`，而是完全不干预（直接 return 放行原版 PASS）**：客户端拿不到服务端 config/仇恨/报价，开 GUI 全靠服务端 openMenu + ClientboundMerchantOffersPacket 驱动，避免误拦村民。
- 新增条件：双手空手、存活、未在交易（`getTradingPlayer()==null` 防 interactAt+interact 重复开窗）、有报价（空表吞交互不开窗，对齐村民没货）。
- 仇恨判定走 `AngerController.isAngry(Mob)`：mod 来源 + 原版 NeutralMob + Brain ATTACK_TARGET 三路。
- `getOffers` 按 PriceTable 实例身份跟随 reload 懒重建（收口旧账④，代价 uses 归零，补货落地前接受）。

直接调 `openTradingScreen(player, getDisplayName(), 0)`（default 方法，走原版 MerchantMenu + ClientboundMerchantOffersPacket）。

## 产出物

- 代码：`trade/TradeInteraction.java`、`mixin/MobMerchantMixin.java`（mobInteract 注入）、`anger/AngerController.java#isAngry`
- 单测：`trade/TradeInteractionTest.java`（8 条真值表，165→173 全绿）
- 真机脚本：`tests/automation/verify_trade_interaction.py`（8/8 PASS）
- Commit：`feat(trade): 实现右键打开交易界面`

## 备注 / 遗留

- **P2（纯原版客户端可交易）已真机闭环（2026-10-12）**：用独立 mc-client-rpc 工程的 runClient（零 PAL 类）连 PAL 服务端，同套 8 例全 PASS，见 `P1-P4-VERIFY.md` §P2。
- 未测：双槽支付成交、maxUses 买光、跨日补货、村民等原生 Merchant 零回归（归 T-TRADE-004/005）。
