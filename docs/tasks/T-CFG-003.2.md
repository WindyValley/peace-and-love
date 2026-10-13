- [x] T-CFG-003.2: reload 后定价表重建

**完成备注：** 2026-10-13 回填：PriceTableService 订阅 reload 监听，签名守卫（锚点/上限/overrides 变才重建，白名单/开关跳过），失败不阻断白名单生效；T-PRICE-003 真机验过 reload 正反两面按需重建（改价 override 即时反映）
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

- [x] reload 成功后触发定价表重建
- [x] 新锚点/手工修正立即反映到后续报价
- [x] 定价表构建失败不影响白名单等其它配置生效（隔离失败域）

## 技术要点

- 依赖 PriceTable 启动构表能力（T-PRICE-003）落地后接入 reload 回调

## 产出物

- 代码：reload → PriceTable.rebuild 接线
- Commit：待提交

## 备注

无
