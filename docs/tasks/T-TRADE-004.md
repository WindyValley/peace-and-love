- [x] T-TRADE-004: RestockManager 每日补货

**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-TRADE-002
**可并行：** T-TRADE-005
**状态：** ✅ done（2026-10-13，对齐村民双时钟；common 单测 173→184 全绿 + 真机 A/B/C/D 全 PASS）

## 目标

每补货周期重置交易次数，自写重置逻辑，**禁用** `Villager.restock()`。

## 来源

- 设计：`../02-design.md` §5.3 每日补货
- 决策：`../adr/003`

## 验收标准

- [x] 游戏时间推进跨过周期时重置所有 offer 的 uses（真机 B：120t 周期，推进 161t 后 uses 全 0）
- [x] `restock_interval_days` 支持小数（config int→double；0.5=12000t，真机用 0.005 天=120t 验在线补货）
- [x] **不调用 `Villager.restock()`**（只调 `MerchantOffer.resetUses()`，无 gossip/demand 副作用）
- [x] 补货判定基于 `level.getGameTime()`（单调世界时钟，非真实时间、不受 `/time set`/睡觉影响；整数天与边界由纯逻辑单测覆盖）
- [x] 玩家不在线/区块卸载期间跨周期，实体加载时补算（真机 C：卸载期间时钟走 231t 跨周期，回来首 tick uses=0；离线只补一次并网格对齐）

## 实现与任务卡初版的差异（以真机为准）

1. **时间用 tick 不用「天」**：`RestockManager.evaluate(gameTime, lastTick, intervalDays)` 纯算术，
   `intervalTicks = round(days*24000)`。补货锚点 = 首次时刻 + 周期整数倍（**网格对齐**），
   离线跨多周期只补一次、锚点推进到不晚于当前的最近网格点，避免补货节奏整体前移。
2. **uses/补货时刻随实体 NBT 持久化**（设计稿 §4.1 已预留，本轮落地）：
   Mixin 注入 `addAdditionalSaveData`/`readAdditionalSaveData`，存 `pal_offers`(MerchantOffers.CODEC)、
   `pal_sig`、`pal_restock`(上次补货 gameTime)。否则玩家走远卸载再回来即可无视限购刷货。
   只对已组装过报价的怪写 NBT（被右键过/从存档恢复），不给野生怪塞数据。
3. **PriceTable 内容指纹 + maxUses 签名**：`getOffers()` 用
   `fingerprint*31 + max_uses_per_day` 作失效签名（取代 003 的「实例身份」判据）。
   改价/改锚点/改限购才重建（uses 归零）；reload 没改内容时保留购买次数（修掉 003 的小瑕疵）。
4. **tick 只处理已有报价的怪**（`pal$offers != null`），绝不为全部野生怪每 tick 组装报价。
5. **顺手接通死配置** `max_uses_per_day`：此前 `TradeSpec.toOffer()` 把 maxUses 写死 1，
   config 从未生效；现 `toOffer(int maxUses)`，builder 从 config 传入。

## 技术要点（实际实现）

补货判定不放 Mixin，抽到 `RestockManager.evaluate(...)` 纯算术，Mixin tick 只取事实与清零。
**语义对齐原版村民 `Villager#shouldRestock()` 的双时钟**（源码核实），但去掉职业经验/
demand 涨价/每日次数上限：

```java
// 两条腿 OR，且要求 hasStockedOut(=任一报价 isOutOfStock，对应村民 needsToRestock)
long today = dayTime / 24000L;                       // dayTime=level.getDayTime()，睡觉/time add 会快进
if (lastGame < 0)        return (false, gameTime, today);                 // 首次只锚定双时钟
if (!hasStockedOut)      return (false, lastGame, lastDay);               // 无售罄:不补,锚点不推进
boolean byInterval = gameTime - lastGame >= max(1, round(intervalDays*24000)); // 单调 getGameTime
boolean byDayChange = today > lastDay;                                    // 睡过一夜/time add
if (byInterval || byDayChange) return (true, gameTime, today);            // 锚点定当前,不网格回卷
return (false, lastGame, lastDay);
```

- **滚动间隔腿**用 `level.getGameTime()`（每 tick+1，命令/睡觉都改不了）。
- **跨自然日腿**用 `level.getDayTime()/24000`：玩家睡觉、`/time add` 都走
  `ServerLevel#setDayTime` 快进（`TimeCommand.addTime` 源码证实），**睡觉据此让怪物提前补货**，
  这是用户明确要求、旧单时钟实现缺失的语义。
- 离线卸载不 tick，重挂首 tick 用两个时钟一次性补算，跨再多也只补一次。
- `resetUses()` 是 `MerchantOffer` public 方法；绝不调 `Villager.restock()`
  （它先 `updateDemand()` 做 catchUpDemand 涨价）。
- 相对旧实现（单 gameTime + 网格对齐 + 锚点无条件前移）的修正：加睡觉腿；加 needsToRestock 门控，
  没人买时锚点不空转；锚点改为定到当前时刻（对齐村民 OR flag，剩余零头并入下一周期）。

## 产出物

- 代码：`trade/RestockManager.java`；Mixin tick + 双锚点 NBT（`pal_restock_game`/`pal_restock_day`，
  兼容旧 `pal_restock`）在 `mixin/MobMerchantMixin.java`
- 测试：`trade/RestockManagerTest.java`（11 例双时钟：首次锚定/滚动间隔/无售罄不补/睡觉跨天/
  半天周期/离线大跳/同一天长间隔/边界）+ `TradeSpecTest` 限购透传；common 184 全绿
- 真机：`tests/automation/verify_restock.py`（A 持久化 / B 在线小数补货 / C 离线补算 /
  **D 睡觉跨天腿**，全 PASS；D 实测 interval=1 天仅 `/time add 24000`，gameTime 只 +25、day+1 即清零）
- Commit：`feat(trade): 实现补货机制与购买次数持久化 T-TRADE-004`

## 备注 / 遗留

- 真机用探针 `setToOutOfStock()` 模拟买光（真实「放绿宝石→成交」链路属 T-TRADE-005）；
  「售罄如何被重置」已验，但「玩家真买一次→uses+1→界面售罄」的端到端等 005 成交接线后复验。
- NBT 持久化仅 NeoForge 真机验过（代码在 common，Fabric 同路径未真机）。
- probe(`trade.probe`) 为真机判定新增回显 `dayTime`/`day` 字段。
