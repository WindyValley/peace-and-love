- [x] T-SCOPE-002: NeutralizationScope 门控判定

**完成备注：** commit a0541af；isNeutralized/canTrade 读当前配置不缓存，NeutralizationService 入口接线；Boss 三场景有单测，完整真值表归 T-TEST-002
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

- [x] `isNeutralized(type) == isAdapted(type) && !inWhitelist(type)`
- [x] `canTrade(type) == isNeutralized(type) && tradingEnabled && (非Boss || bossTradingEnabled)`
- [x] 第三方 Mod 生物一律返回 false（不在已适配列表）
- [x] 白名单变更后立即生效（读配置当前值，不缓存）
- [x] 门控逻辑实现并在运行时接线（NeutralizationService 入口调用 isNeutralized/canTrade，读当前配置不缓存）；真值表完整用例由 T-TEST-002 追踪补齐

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
