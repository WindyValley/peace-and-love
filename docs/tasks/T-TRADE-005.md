- [ ] T-TRADE-005: NBT 持久化

**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-TRADE-004
**可并行：** T-NEUT-004

## 目标

把 `lastRestockDay` 与已生成的 offers 存入实体 NBT，跨存档保持。

## 来源

- 设计：`../02-design.md` §3.4

## 验收标准

- [ ] `pal$lastRestockDay` 写入 NBT（key: `PalLastRestockDay`）
- [ ] offers 序列化（复用 `MerchantOffers#createTag`）
- [ ] 读档后交易次数状态正确恢复
- [ ] 旧存档（无该 NBT）不报错，按首次生成处理
- [ ] 白名单内生物不写入冗余 NBT

## 技术要点

在 `Mob#addAdditionalSaveData` / `readAdditionalSaveData` 注入。
NBT 体积控制：offers 可选择**不持久化**，读档后按定价表重建，
只存 `lastRestockDay` + 各 offer 的 uses 计数，更省空间。设计倾向后者。

## 产出物

- 代码：`mixin/MobMerchantMixin.java`
- Commit：`feat(trade): 实现交易状态 NBT 持久化`

## 备注

无
