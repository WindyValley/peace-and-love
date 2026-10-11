- [ ] T-PRICE-003: PriceTable 启动时构建与缓存

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

- [ ] 服务端启动完成后自动构建
- [ ] `/peaceandlove reload` 后重建
- [ ] 查询 `getPrice(EntityType, Item)` 为 O(1)
- [ ] 构建耗时打 INFO 日志（性能基线）
- [ ] 表为不可变，构建后不可修改

## 技术要点

用 `Map<EntityType<?>, Map<Item, Integer>>` 或扁平化 record key。
构建应在主线程完成，避免与交易请求竞态。

## 产出物

- 代码：`pricing/PriceTable.java`
- Commit：`feat(pricing): 实现定价表构建与缓存`

## 备注

无
