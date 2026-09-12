# T-PRICE-001: LootTableScanner 解析战利品表算 epk

**状态：** todo
**优先级：** P0
**预估：** 6h
**Owner：** agent
**依赖：** T-SETUP-003
**可并行：** T-CFG-002

## 目标

扫描 38 个生物的原版战利品表，计算每个掉落物的「每击杀期望产出」(epk)。

## 来源

- 设计：`../02-design.md` §3.3 定价引擎、§5.1 启动时构建定价表
- 决策：`../adr/003`
- spike：`spikes/r1-loot/price_algo_v3.py`

## 验收标准

- [ ] 解析出 **110 条**「生物 × 掉落物」条目
- [ ] epk 计算含抽取概率、数量范围期望、多池叠加
- [ ] 排除稀有掉落中的装备类（不参与交易）
- [ ] 与 spike 产出的 `final_pricing_128.json` 逐条比对，epk 一致
- [ ] 解析失败的生物打 WARN 但不崩服

## 技术要点

**服务端启动后**执行（战利品表在 `ReloadableServerResources` 就绪后才可读）。
监听 `ServerLifecycleEvents` 或 Architectury 的等价事件。

epk 公式：`epk = Σ(pool_rolls × entry_weight/total_weight × E[count])`
注意 `LootItemConditions` 中的 `killed_by_player` 与 `looting` 加成不计入基准 epk。

## 产出物

- 代码：`pricing/LootTableScanner.java`
- 测试：`LootTableScannerTest.java`
- Commit：`feat(pricing): 实现战利品表解析与 epk 计算`

## 备注

spike 阶段已验证算法可行，本任务是把 Python 原型翻译为 Java。
