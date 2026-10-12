- [x] T-PRICE-004: 定价单调性自检

**完成备注：** 真机PASS 2026-10-12：默认自检INFO(70条/撞下限3/上限0/无逆序)不阻断启动；填反override触发WARN检出3对逆序列前3。commit 48b565a，common 158绿
**优先级：** P1
**预估：** 2h
**Owner：** agent
**依赖：** T-PRICE-003
**可并行：** T-TRADE-002

## 目标

启动时自检定价表的单调性与边界，异常时打 WARN 提醒管理员参数配置不当。

## 来源

- 设计：`../02-design.md` §3.3

## 验收标准

- [x] 检测同一生物内「epk 更小但价格更低」的逆序对
- [x] 检测撞上限/下限的条目数并打 INFO
- [x] 逆序对存在时打 WARN 并列出前 5 个
- [x] 自检本身不阻断启动

## 技术要点

- spike 全游戏 110 条实测「0 撞上限、11 撞下限」；本模组只扫 38 适配生物=70 条，真机实测撞下限 3、撞上限 0（域不同，数字不同，均正常）。逆序对只可能来自 price_overrides 填反或锚点过激，纯曲线天然单调。

## 产出物

- 代码：`pricing/PriceTable.java`（`selfCheck` 纯函数 + `SelfCheck` 记录）、`pricing/PriceTableService.java`（构表后落自检日志，try/catch 兜底）
- 测试：`PriceTableTest` +5（默认健康/override 填反检出逆序/同价平台期不误报/撞上下限计数/空表不抛）；common 158 绿
- Commit：48b565a

## 备注

- 真机验证 PASS（2026-10-12，测试服，verify 构建 CRC32 核对部署）：默认参数 INFO「70 条，撞下限 3、撞上限 0」、无逆序、不阻断启动；故意填反 zombie_villager 的 rotten_flesh=120 后，WARN 检出 3 对逆序并列出前 3 个定位串；还原配置后恢复，无 ERROR。
