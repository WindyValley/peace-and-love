- [x] T-TEST-002.1: 门控单测：Boss/开关/白名单场景

**完成备注：** NeutralizationScopeTest 现覆盖 Boss/全局开关/白名单/isBoss（a0541af）；真值表补齐在 .2
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SCOPE-002
**可并行：** T-TEST-001, T-TEST-003

## 目标

NeutralizationScope 已有的 JUnit 覆盖：Boss 交易门控、全局交易开关、白名单生物、isBoss 等。

## 来源

- 拆分自：T-TEST-002

## 验收标准

- [x] 凋灵：已适配+不在默认白名单 → isNeutralized=true 且默认 canTrade=false
- [x] boss_trading_enabled=true 后凋灵 canTrade=true
- [x] trading_enabled=false 时普通生物 canTrade=false
- [x] 白名单生物（pillager）canTrade=false
- [x] isBoss：凋灵/监守者 true，僵尸 false

## 技术要点

- NeutralizationScopeTest 现有用例（bootstrap 注册后纯静态断言）

## 产出物

- 测试：scope/NeutralizationScopeTest.java
- Commit：a0541af

## 备注

现有门控场景已覆盖；真值表缺口见 .2
