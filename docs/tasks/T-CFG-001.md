# T-CFG-001: PalConfig 数据类与默认值

**状态：** todo
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

- [ ] 默认白名单**恰好 6 项**：掠夺者/卫道士/唤魔者/恼鬼/幻翼/潜影贝
- [ ] **凋灵与监守者不在默认白名单**
- [ ] `price_max=128`、`epk_cheap=2.0`、`epk_rare=0.005`
- [ ] `restock_interval_days=1.0`、`anger_cooldown_seconds=30`、`kin_alert_radius=4.0`
- [ ] `trading_enabled=true`、`boss_trading_enabled=false`
- [ ] 单测断言默认白名单 size == 6

## 技术要点

用 record 或不可变类；字段名与 JSON key 完全一致，便于序列化。

## 产出物

- 代码：`config/PalConfig.java`
- 测试：`PalConfigDefaultsTest.java`
- Commit：`feat(config): 定义配置数据类与默认值`

## 备注

无
