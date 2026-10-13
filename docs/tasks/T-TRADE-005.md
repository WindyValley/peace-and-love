- [x] T-TRADE-005: 真实成交链路（选报价→扣款出货→uses+1→售罄/限购→补货后再购）

**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-TRADE-004
**可并行：** T-NEUT-004
**状态：** ✅ done（2026-10-13，common 单测全绿 + 真机两轮全 PASS）

> ⚠️ 任务卡历史错位：原标题/验收写的是「NBT 持久化」，但那部分已在 T-TRADE-004
> 完成（pal_offers/pal_sig/pal_restock_game/pal_restock_day 随实体存盘，真机 A 持久化 PASS）。
> 005 真正的缺口是**真实成交闭环**，本卡按实际完成内容重写。

## 目标

玩家在右键打开的原版交易 GUI 里真金白银地完成一次购买：放绿宝石 → 选报价 →
取结果时服务端扣款、发出掉落物、报价 uses+1，买光后该条售罄；补货周期过后能再次购买。

## 验收标准（真机，全部 PASS）

- [x] 右键开窗后客户端能驱动「选报价」「取结果」（mc-client-rpc 新增 trade.select/take/status/close）
- [x] 选报价后绿宝石从背包挪入货币槽、结果槽出货
- [x] 取结果：绿宝石按**报价真实价**扣减（不是货币槽被填满的 64）、产物正确入包、报价 uses+1
- [x] maxUses=1 买光后**客户端 GUI 即时显示售罄**（红叉），无需重开窗口
- [x] 买光后再次选该报价无法成交（限购服务端权威）
- [x] 买光 → 睡觉腿补货（/time add 24000）→ 重开窗口 uses 归零 → 可再次真实购买，产物累计、新周期再次售罄

## 关键事实（读原版源码核实，非推断）

- 成交链路**全部基于 `Merchant` 接口、零 Villager 强转**：
  - 开窗：`Merchant#openTradingScreen`（default）→ `new MerchantMenu(id, inv, this)` + 首发包；
  - 选报价：客户端 `MerchantScreen.postButtonClick` = `menu.setSelectionHint+tryMoveItems`
    + 发 `ServerboundSelectTradePacket`；服务端 `handleSelectTrade` 权威地再 `tryMoveItems`；
  - 取结果：`MerchantResultSlot#onTake` → `MerchantOffer.take(costAstack,costBstack)` 按
    `getCostA()/getCostB()` 数量 shrink 货币（含 demand/乘数修正，本 mod multiplier=0 即配置价），
    随后回调 `Merchant#notifyTrade(offer)` 与 `getVillagerXp/overrideXp`。
- **货币槽会被客户端填满一整组（64）**：`MerchantMenu.moveFromInventoryToPaymentSlot` 尽量填，
  不看需求量；服务端成交只按真实价 shrink，多放的留在槽里、关窗 `placeItemBackInInventory` 退回。
  故「成交价」必须读报价 `getCostA/B`，不能读货币槽 count。

## 本轮生产代码修复（PAL）

`MobMerchantMixin#notifyTrade`：`offer.increaseUses()` 后，若正在交易的玩家容器是
MerchantMenu，则 `ServerPlayer#sendMerchantOffers(containerId, offers, 0, xp, showBar, canRestock)`
重发更新后的报价。对齐原版村民 `Villager#resendOffersToTradingPlayer`（原版仅在成交路径重发，
开窗只发一次）。**不修则服务端 uses+1 已限购，但当前打开的 GUI 不刷新、仍显示可买。**
客户端收包 `ClientPacketListener#handleMerchantOffers` → `menu.setOffers(...)`，即时显示红叉。

## 驱动侧修复（独立仓 mc-client-rpc，commit 3344ae4）

- 新增 `trade.status / trade.select / trade.take / trade.close`（一帧式原语，多帧时序由脚本编排）。
- 修自动关窗 bug：旧实现 `mc.setScreen(null)` 只触发屏幕 `removed()` 本地清理、**不发
  ServerboundContainerClosePacket**；真玩家按 Esc 走 `onClose→LocalPlayer.closeContainer` 才发包。
  不发包则服务端 MerchantMenu 不 removed、`setTradingPlayer(null)` 不执行，成交关窗后再次右键
  被「已在交易」门控挡下（实测 distance=1.0/空手/clientResult PASS 但不开窗）。
  `trade.close` 与 `player.interact(autoClose=true)` 均改为 `player.closeContainer()`。

## 产出物

- PAL 代码：`mixin/MobMerchantMixin#notifyTrade`（成交后重发报价）
- PAL 真机脚本：`tests/automation/verify_trade_purchase.py`（单次成交 A1~A5）、
  `tests/automation/verify_trade_restock_repurchase.py`（买光→补货→再购 S0/B1/B2）
- mc-client-rpc：4 个 trade.* 原语 + 关窗发包修复（commit 3344ae4）

## 已测 / 未测

- 已真机测：僵尸（腐肉，真实价 16 绿宝石）单次成交全链路、限购、即时售罄、睡觉补货后再购。
- 未测：双槽（单价 >64）真实支付、其余适配怪种成交、Fabric 端、村民/流浪商人原生 Merchant 零回归。
- 交易交互约定：本 mod 003 门控刻意要求**空手右键**开窗，货币由 GUI 自动从背包挪入，
  不支持手持绿宝石直接点怪交易（与村民不同，是既定设计）。
