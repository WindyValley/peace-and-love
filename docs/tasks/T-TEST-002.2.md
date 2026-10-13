- [x] T-TEST-002.2: 门控真值表补齐：4组合/第三方/动态

**完成备注：** 2026-10-13：新增 NeutralizationScopeTruthTableTest，@CsvSource 参数化 4 组合(isAdapted×白名单)、末影龙未适配直接断言 false(含列入白名单)、未知/第三方 id 无效且对白名单惰性不改变任何判定、白名单动态变更同一入口立即翻转
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SCOPE-002、T-TEST-002.1
**可并行：** T-TEST-001, T-TEST-003

## 目标

把 NeutralizationScope 真值表补齐为参数化完整覆盖，并直接断言未适配与配置动态生效。

## 来源

- 拆分自：T-TEST-002

## 验收标准

- [x] 参数化覆盖 4 种基础组合（isAdapted × inWhitelist）的 isNeutralized/canTrade
- [x] 末影龙（未适配）无论是否在白名单，isNeutralized 直接断言为 false（不只走 isIneffectiveWhitelistEntry）
- [x] 第三方 Mod 生物（未注册/未知 id）一律 false
- [x] 白名单动态变更后，同一判定入口立即改变（不缓存）的显式断言

## 技术要点

- 用 ParameterizedTest/CsvSource 表达真值表，避免手写重复

## 产出物

- 测试：扩充 NeutralizationScopeTest
- Commit：待提交

## 备注

无
