# T-SCOPE-002: NeutralizationScope 门控判定

**状态：** todo
**优先级：** P0
**预估：** 3h
**Owner：** agent
**依赖：** T-SCOPE-001, T-CFG-001
**可并行：** T-PRICE-001

## 目标

实现「已适配列表 ∩ 非白名单」双重决策门控，这是全项目的行为总开关。

## 来源

- 设计：`../02-design.md` §3.1 生效范围判定
- 决策：`../adr/004`
- 需求：FR-1.5

## 验收标准

- [ ] `isNeutralized(type) == isAdapted(type) && !inWhitelist(type)`
- [ ] `canTrade(type) == isNeutralized(type) && tradingEnabled && (非Boss || bossTradingEnabled)`
- [ ] 第三方 Mod 生物一律返回 false（不在已适配列表）
- [ ] 白名单变更后立即生效（读配置当前值，不缓存）
- [ ] 单测覆盖真值表全部 4 种组合

## 技术要点

**这是全项目最关键的判定**，务必先写单测再实现。

真值表：
| 已适配 | 在白名单 | 结果 |
|--------|---------|------|
| ✅ | ❌ | **中立化** |
| ✅ | ✅ | 保持原版 |
| ❌ | ❌ | 保持原版 |
| ❌ | ✅ | 保持原版（配置无效，打 INFO） |

## 产出物

- 代码：`scope/NeutralizationScope.java`
- 测试：`NeutralizationScopeTest.java`
- Commit：`feat(scope): 实现双重决策门控`

## 备注

无
