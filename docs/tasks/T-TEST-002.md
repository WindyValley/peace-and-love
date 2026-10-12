- [-] T-TEST-002: 单元测试：门控逻辑真值表

**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SCOPE-002
**可并行：** T-TEST-001, T-TEST-003

## 目标

覆盖「已适配 × 白名单」四种组合，以及交易门控的额外条件。

## 来源

- 设计：`../02-design.md` §3.1

## 子任务（状态由子任务聚合，勿手改本卡状态）

- [x] T-TEST-002.1: 门控单测：Boss/开关/白名单场景
- [ ] T-TEST-002.2: 门控真值表补齐：4组合/第三方/动态

## 技术要点

纯逻辑测试，不需要 MC 运行时，用 mock 的 EntityType 即可。

## 产出物

- 测试：`NeutralizationScopeTest.java`
- Commit：`test(scope): 添加门控真值表测试`

## 备注

无
