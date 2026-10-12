- [-] T-PRICE-003: PriceTable 启动时构建与缓存

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

- [ ] 服务端启动完成后自动构建（SERVER_STARTED，数据包就绪；接线已写，生命周期触发待真机验证）
- [ ] `/peaceandlove reload` 后重建（订阅 ConfigManager 重载监听；仅当锚点/上限/override 变化才重建，白名单等不影响价格的变更跳过）
- [x] 查询为 O(1)：`offersFor(EntityType)` 走 byEntity、`offersFor(EntityType, Item)` 走扁平 byEntityItem 索引；同一物品互斥分支多条报价保留为 List（史莱姆黏液球 2 条），不压成单值（PriceTableTest 覆盖）
- [x] 构建耗时打 INFO 日志（扫描与构表各一条，含报价数/告警数，性能基线）
- [x] 表为不可变，构建后不可修改（Map/List.copyOf 冻结，返回列表不可改，有单测）

## 技术要点

用 `Map<EntityType<?>, Map<Item, Integer>>` 或扁平化 record key。
构建应在主线程完成，避免与交易请求竞态。

## 产出物

- 代码：`pricing/PriceTable.java`（不可变表+纯构建）、`pricing/PriceTableService.java`（SERVER_STARTED 构表/reload 重建）、`PeaceAndLove.init()` 接线
- 测试：`pricing/PriceTableTest.java`（9）；common 全量 151 绿
- Commit：0d85b2f

## 备注

- 实现修正任务卡早期设想：查询不是 `getPrice(EntityType,Item)` 单值，而是 `offersFor(...)` 返回 List —— 同一物品互斥分支有多条报价（史莱姆黏液球 2 条），压成单值会丢掉落量维度。依据黄金基线 final_pricing_128.json 与设计 §5.1。
- 验收 1/2（SERVER_STARTED 自动构表、reload 重建）属运行时行为，接线已写但待真机：看启动日志「PAL 定价表构建完成」报价数对齐基线（110 条），并验改锚点 reload 后重建、白名单变更不重建。真机时机待定（可随 T-TRADE-003 一起，或现在部署看日志）。
