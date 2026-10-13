- [x] T-PRICE-003: PriceTable 启动时构建与缓存

**完成备注：** 真机 PASS 2026-10-12：启动构表38→70条、与黄金基线逐条等值、reload正反两面按需重建；顺带修reload摘要漏字段(a2288e8)。common 153绿
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-PRICE-002
**可并行：** T-TRADE-001

## 目标

在服务端启动与配置重载时构建定价表并缓存，供交易系统查询。

## 来源

- 设计：`../02-design.md` §5.1

## 验收标准

- [x] 服务端启动完成后自动构建（SERVER_STARTED，数据包就绪；真机已验证：38→70 条）
- [x] `/peaceandlove reload` 后重建（订阅 ConfigManager 重载监听；仅当锚点/上限/override 变化才重建，白名单等不影响价格的变更跳过）
- [x] 查询为 O(1)：`offersFor(EntityType)` 走 byEntity、`offersFor(EntityType, Item)` 走扁平 byEntityItem 索引；同一物品互斥分支多条报价保留为 List（史莱姆黏液球 2 条），不压成单值（PriceTableTest 覆盖）
- [x] 构建耗时打 INFO 日志（扫描与构表各一条，含报价数/告警数，性能基线）
- [x] 表为不可变，构建后不可修改（Map/List.copyOf 冻结，返回列表不可改，有单测）

## 技术要点

用 `Map<EntityType<?>, Map<Item, Integer>>` 或扁平化 record key。
构建应在主线程完成，避免与交易请求竞态。

## 产出物

- 代码：`pricing/PriceTable.java`（不可变表+纯构建）、`pricing/PriceTableService.java`（SERVER_STARTED 构表/reload 重建）、`PeaceAndLove.init()` 接线
- 测试：`pricing/PriceTableTest.java`（9）、ConfigManagerTest 摘要 +2；common 全量 153 绿
- Commit：0d85b2f（构表/缓存/接线）、a2288e8（真机发现的 reload 摘要漏字段修复）

## 备注

- 实现修正任务卡早期设想：查询不是 `getPrice(EntityType,Item)` 单值，而是 `offersFor(...)` 返回 List —— 同一物品互斥分支有多条报价（史莱姆黏液球 2 条），压成单值会丢掉落量维度。依据黄金基线 final_pricing_128.json 与设计 §5.1。
- 真机验证 PASS（2026-10-12，测试服 192.0.2.10，-PenableVerifyRpc=true 构建，逐条目 CRC32 核对部署）：
  - 启动自动构表：日志「38 生物 → 70 条可定价掉落（5ms）」「定价表构建完成：30 生物、70 条报价（3~4ms）」，无 ERROR。
  - 数据源黄金交叉：真机 70 条与黄金基线中属于 38 适配生物的 70 条逐条 epk/count_max 全等值；黄金 price_128 用当前曲线复算全吻合；史莱姆两条互斥报价正确保留。
  - reload 按需重建：改 epk_rare/price_max 触发重建；改 anger/kin 等非定价字段签名守卫跳过、不重建（正反两面均验）。配置已还原默认。
  - 真机附带发现并修复：reload 回执曾对锚点变更误报「无变更」（summarize 漏字段），已由 a2288e8 修复并真机复验回执正确。
