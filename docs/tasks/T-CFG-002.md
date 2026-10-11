- [ ] T-CFG-002: 配置 JSON 读写与容错

**优先级：** P0
**预估：** 4h
**Owner：** agent
**依赖：** T-CFG-001
**可并行：** T-PRICE-001

## 目标

实现配置文件的加载、保存、校验；损坏或缺字段时回退默认值并告警。

## 来源

- 设计：`../02-design.md` §6
- 需求：FR-3.1

## 验收标准

- [ ] 首次启动自动生成 `config/peaceandlove.json`
- [ ] 字段缺失时用默认值补齐并回写
- [ ] JSON 语法错误时**不崩服**，回退全默认 + WARN 日志
- [ ] 数值越界时 clamp 并 WARN（如 price_max < 1）
- [ ] 未知字段保留不丢弃（向前兼容）

## 技术要点

用 GSON（MC 自带）。注意 `price_max` 上限受 `MerchantOffer` 双槽限制，最大 128。

## 产出物

- 代码：`config/ConfigLoader.java`
- 测试：`ConfigLoaderTest.java`（含损坏 JSON 用例）
- Commit：`feat(config): 实现配置读写与容错`

## 备注

无
