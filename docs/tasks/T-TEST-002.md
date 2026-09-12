# T-TEST-002: 单元测试：门控逻辑真值表

**状态：** todo
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SCOPE-002
**可并行：** T-TEST-001, T-TEST-003

## 目标

覆盖「已适配 × 白名单」四种组合，以及交易门控的额外条件。

## 来源

- 设计：`../02-design.md` §3.1

## 验收标准

- [ ] 4 种基础组合全覆盖
- [ ] 凋灵：已适配 + 不在默认白名单 → **中立化**
- [ ] 末影龙：未适配 → 无论白名单如何都保持原版
- [ ] 第三方 Mod 生物 → 一律 false
- [ ] `trading_enabled=false` → 中立但不可交易
- [ ] `boss_trading_enabled=false` + 凋灵 → 中立但不开界面
- [ ] 白名单动态变更后判定立即改变

## 技术要点

纯逻辑测试，不需要 MC 运行时，用 mock 的 EntityType 即可。

## 产出物

- 测试：`NeutralizationScopeTest.java`
- Commit：`test(scope): 添加门控真值表测试`

## 备注

无
