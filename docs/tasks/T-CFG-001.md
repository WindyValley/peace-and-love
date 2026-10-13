- [x] T-CFG-001: PalConfig 数据类与默认值

**完成备注：** commit 6b097b1；PalConfigDefaultsTest 10 例：默认白名单恰好6、凋灵/监守者不在、锚点 128/2.0/0.005、开关默认值全断言
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SETUP-003
**可并行：** T-SCOPE-001

## 目标

定义配置数据类，含全部字段与默认值（特别是 6 项默认白名单）。

## 来源

- 设计：`../02-design.md` §6 配置文件设计
- 需求：FR-3.1

## 验收标准

- [x] 默认白名单**恰好 6 项**：掠夺者/卫道士/唤魔者/恼鬼/幻翼/潜影贝
- [x] **凋灵与监守者不在默认白名单**
- [x] `price_max=128`、`epk_cheap=2.0`、`epk_rare=0.005`
- [x] `restock_interval_days=1.0`、`anger_cooldown_seconds=30`、`kin_alert_radius=4.0`
- [x] `trading_enabled=true`、`boss_trading_enabled=false`
- [x] 单测断言默认白名单 size == 6

## 技术要点

用 record 或不可变类；字段名与 JSON key 完全一致，便于序列化。

## 产出物

- 代码：`config/PalConfig.java`
- 测试：`PalConfigDefaultsTest.java`
- Commit：`feat(config): 定义配置数据类与默认值`

## 备注

无
