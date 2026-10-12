- [ ] T-CFG-003.2: reload 后定价表重建

**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-PRICE-003（PriceTable）、T-PRICE-002.2（配置锚点）
**可并行：** T-PRICE-002

## 目标

配置热重载后，定价表用新锚点（epk_cheap/epk_rare/price_max）与 price_overrides 重建，供报价使用。

## 来源

- 拆分自：T-CFG-003

## 验收标准

- [ ] reload 成功后触发定价表重建
- [ ] 新锚点/手工修正立即反映到后续报价
- [ ] 定价表构建失败不影响白名单等其它配置生效（隔离失败域）

## 技术要点

- 依赖 PriceTable 启动构表能力（T-PRICE-003）落地后接入 reload 回调

## 产出物

- 代码：reload → PriceTable.rebuild 接线
- Commit：待提交

## 备注

无
