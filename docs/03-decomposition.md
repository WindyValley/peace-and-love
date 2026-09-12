# Peace And Love — 任务拆分

- 版本：v1.0
- 日期：2026-09-11
- 依据：`02-design.md` v1.0、`adr/001~004`、`P1-P4-VERIFY.md`
- 团队规模：**1 人 + AI agent 协作**（非多人团队，故 Owner 主要区分「可委派」与「需人工决策」）
- 任务粒度：单个任务 2~8 人时

---

## 1. 模块树

```
peace-and-love/
├── common/                                  # 全部业务逻辑（跨加载器）
│   └── src/main/java/top/windyvalley/peaceandlove/
│       ├── PeaceAndLove.java                # 入口
│       ├── config/                          # M1 配置层
│       │   ├── PalConfig.java
│       │   ├── ConfigLoader.java
│       │   └── ConfigCommand.java
│       ├── scope/                           # M2 生效范围
│       │   ├── AdaptedMobs.java             # 38 个常量（不可变）
│       │   └── NeutralizationScope.java     # 门控判定
│       ├── pricing/                         # M3 定价引擎
│       │   ├── LootTableScanner.java
│       │   ├── PriceCalculator.java
│       │   └── PriceTable.java
│       ├── trade/                           # M4 交易系统
│       │   ├── TradeOfferBuilder.java
│       │   └── RestockManager.java
│       ├── neutralize/                      # M5 中立化
│       │   ├── NeutralizeStrategy.java
│       │   ├── GoalBasedStrategy.java
│       │   ├── BrainBasedStrategy.java
│       │   ├── GoalSnapshot.java
│       │   └── special/                     # 10 个特殊适配
│       ├── anger/                           # M6 仇恨控制
│       │   ├── AngerController.java
│       │   └── KinAlerter.java
│       └── mixin/                           # M7 注入层
│           ├── MobMerchantMixin.java
│           └── LivingEntityHurtMixin.java
├── fabric/                                  # M8 平台适配
├── neoforge/                                # M8 平台适配
└── .github/workflows/                       # M9 CI/CD
```

---

## 2. WBS（按交付物反推）

```
v1.0 发布物
├── 两个可用 jar（Fabric / NeoForge）
│   ├── 38 个生物中立化生效
│   ├── 交易系统可用（价格 / 每日 1 次 / 补货）
│   ├── 仇恨机制符合语义（仅玩家攻击触发）
│   └── 配置热重载 + 白名单命令
├── 测试套件
│   ├── 单元测试（定价 / 门控 / 补货，不依赖 MC 运行时）
│   └── 真机验证清单（服务端实测）
├── 发布材料
│   ├── README（中英）
│   ├── Modrinth / CurseForge 页面文案
│   └── LICENSE + 版权声明
└── CI
    └── GitHub Actions 双端构建
```

---

## 3. Epic 划分

| Epic | 名称 | 任务数 | 关键路径 | 说明 |
|------|------|--------|---------|------|
| **SETUP** | 工程骨架 | 4 | ★ | 由 `spikes/p1-p3-probe/` 演进 |
| **SCOPE** | 生效范围 | 3 | ★ | 其他模块的前置 |
| **CFG** | 配置系统 | 4 | ★ | 门控依赖它 |
| **PRICE** | 定价引擎 | 4 | | 可与 NEUT 并行 |
| **TRADE** | 交易系统 | 5 | ★ | 依赖 PRICE |
| **NEUT** | 中立化 | 7 | ★ | 含 10 个特殊适配 |
| **ANGER** | 仇恨控制 | 4 | ★ | 与 NEUT 强耦合 |
| **TEST** | 测试 | 4 | | 贯穿 |
| **REL** | 发布 | 5 | | 末期 |

**合计 40 个任务。**

---

## 4. 任务清单

### Epic SETUP —— 工程骨架

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-SETUP-001 | 由探针工程演进为正式工程（清理探针代码、改 modid/版本） | 3h | — | P0 |
| T-SETUP-002 | Git 仓库初始化 + .gitignore + 首次提交 | 1h | T-SETUP-001 | P0 |
| T-SETUP-003 | 包结构与分层骨架（空类 + package-info） | 2h | T-SETUP-001 | P0 |
| T-SETUP-004 | GitHub Actions 双端构建 CI | 3h | T-SETUP-002 | P1 |

> ⚠️ T-SETUP-001 必须保留探针工程已验证的 Gradle 配置：
> Gradle 8.10.2 wrapper、子模块 `loom.platform`、空 accesswidener。

### Epic SCOPE —— 生效范围（门控）

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-SCOPE-001 | `AdaptedMobs` 38 个常量 + Goal/Brain 分组标记 | 3h | T-SETUP-003 | P0 |
| T-SCOPE-002 | `NeutralizationScope` 门控判定（已适配 ∩ 非白名单） | 3h | T-SCOPE-001, T-CFG-001 | P0 |
| T-SCOPE-003 | 末影龙等未适配生物的 INFO 日志提示 | 1h | T-SCOPE-002 | P2 |

### Epic CFG —— 配置系统

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-CFG-001 | `PalConfig` 数据类 + 默认值（含 6 项默认白名单） | 3h | T-SETUP-003 | P0 |
| T-CFG-002 | JSON 读写 + 校验 + 容错（损坏时回退默认） | 4h | T-CFG-001 | P0 |
| T-CFG-003 | `/peaceandlove reload` 热重载命令 | 3h | T-CFG-002 | P0 |
| T-CFG-004 | `/peaceandlove whitelist add\|remove\|list` 命令 | 4h | T-CFG-003 | P0 |

### Epic PRICE —— 定价引擎

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-PRICE-001 | `LootTableScanner` 解析战利品表算 epk | 6h | T-SETUP-003 | P0 |
| T-PRICE-002 | `PriceCalculator` 对数曲线实现 | 3h | T-PRICE-001 | P0 |
| T-PRICE-003 | `PriceTable` 启动时构建 + 缓存 | 3h | T-PRICE-002 | P0 |
| T-PRICE-004 | 单调性自检（启动时断言，异常打 WARN） | 2h | T-PRICE-003 | P1 |

> spike 已产出 `final_pricing_128.json` 作为**黄金基准**，T-PRICE-004 可直接比对。

### Epic TRADE —— 交易系统

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-TRADE-001 | `MobMerchantMixin` 注入 Merchant（10 abstract） | 5h | T-SCOPE-002 | P0 |
| T-TRADE-002 | `TradeOfferBuilder` 构建 MerchantOffers | 4h | T-PRICE-003, T-TRADE-001 | P0 |
| T-TRADE-003 | 右键交互打开 GUI（复用 `openTradingScreen`） | 3h | T-TRADE-001 | P0 |
| T-TRADE-004 | `RestockManager` 每游戏日重置 uses | 4h | T-TRADE-002 | P0 |
| T-TRADE-005 | NBT 持久化（lastRestockDay + offers） | 3h | T-TRADE-004 | P0 |

### Epic NEUT —— 中立化

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-NEUT-001 | `NeutralizeStrategy` 接口 + `GoalSnapshot` | 3h | T-SCOPE-002 | P0 |
| T-NEUT-002 | `GoalBasedStrategy`（32 个，用 `removeAllGoals`） | 6h | T-NEUT-001 | P0 |
| T-NEUT-003 | `BrainBasedStrategy`（6 个，每 tick 擦 ATTACK_TARGET） | 6h | T-NEUT-001 | P0 |
| T-NEUT-004 | `restore()` 可逆还原（白名单移入时） | 4h | T-NEUT-002, T-NEUT-003 | P0 |
| T-NEUT-005 | 特殊适配 A 组：潜影贝/幻翼/袭击系3/恼鬼 | 8h | T-NEUT-002 | P0 |
| T-NEUT-006 | 特殊适配 B 组：凋灵/监守者 | 5h | T-NEUT-002, T-NEUT-003 | P0 |
| T-NEUT-007 | 特殊适配 C 组：末影人（凝视）/僵尸猪灵（群体报复） | 5h | T-NEUT-002 | P0 |

> T-NEUT-007 来自 **P4 验证新发现**，原设计没有这两个。

### Epic ANGER —— 仇恨控制

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-ANGER-001 | `LivingEntityHurtMixin` 注入点（仅玩家攻击） | 4h | T-NEUT-001 | P0 |
| T-ANGER-002 | `AngerController` 状态机 + 单目标锁定 | 5h | T-ANGER-001 | P0 |
| T-ANGER-003 | `KinAlerter` 同族示警（4 格 / 单层 / 禁链式） | 5h | T-ANGER-002 | P0 |
| T-ANGER-004 | 脱战冷却 30 秒恢复中立 | 3h | T-ANGER-002 | P0 |

> ⚠️ 三条硬约束（用户两次强调）必须在这四个任务中逐条落实：
> 仅玩家攻击触发 / 锁定攻击者本人 / NPC 攻击不介入。

### Epic TEST —— 测试

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-TEST-001 | 单元测试：定价（比对 `final_pricing_128.json`） | 4h | T-PRICE-004 | P0 |
| T-TEST-002 | 单元测试：门控逻辑真值表 | 3h | T-SCOPE-002 | P0 |
| T-TEST-003 | 单元测试：补货周期边界 | 3h | T-TRADE-004 | P0 |
| T-TEST-004 | **P2 验证**：原版客户端连模组服务端交易 | 3h | T-TRADE-003 | P0 |

### Epic REL —— 发布

| ID | 标题 | 预估 | 依赖 | 优先级 |
|----|------|------|------|--------|
| T-REL-001 | 真机验证清单逐条执行（服务端实测） | 8h | 全部 P0 | P0 |
| T-REL-002 | README 中英双语（面向玩家，非开发日志） | 4h | T-REL-001 | P0 |
| T-REL-003 | LICENSE + 版权声明核实 | 2h | — | P0 |
| T-REL-004 | Modrinth / CurseForge 页面文案 + 截图 | 4h | T-REL-002 | P0 |
| T-REL-005 | 打 tag + 发布（**须用户确认后执行**） | 2h | T-REL-004 | P0 |

> 🔒 T-REL-005 **不得自动执行** —— 发布决策必须由用户显式下达。

---

## 5. 关键路径

```
T-SETUP-001 → T-SETUP-003 → T-CFG-001 → T-SCOPE-002
    → T-NEUT-001 → T-NEUT-002 → T-NEUT-005/006/007
    → T-ANGER-001 → T-ANGER-002 → T-ANGER-003
    → T-REL-001 → T-REL-005
```

**关键路径总长约 62 人时**（约 8~10 个工作日，单人）。

定价链（`T-PRICE-001~004`）不在关键路径上，**可与中立化并行**。

---

## 6. 并行机会

| 批次 | 可同时进行的任务 | 说明 |
|------|----------------|------|
| 批 1 | T-CFG-001~004 ∥ T-PRICE-001~004 | 配置与定价互不依赖 |
| 批 2 | T-NEUT-005 ∥ T-NEUT-006 ∥ T-NEUT-007 | 三组特殊适配彼此独立 |
| 批 3 | T-TEST-001 ∥ T-TEST-002 ∥ T-TEST-003 | 三类单测独立 |
| 批 4 | T-REL-002 ∥ T-REL-003 ∥ T-REL-004 | 文档类并行 |

---

## 7. Sprint 划分

### Sprint 1（第 1~5 天）—— 骨架与基础设施

| Task | Est | 说明 |
|------|-----|------|
| T-SETUP-001~004 | 9h | 工程 + Git + CI |
| T-CFG-001~004 | 14h | 配置全链路 |
| T-SCOPE-001~003 | 7h | 门控 |
| **小计** | **30h** | |

**里程碑 M1**：能启动服务端，`/peaceandlove reload` 与 `whitelist` 命令可用，门控判定正确（但还没有任何行为改变）。

### Sprint 2（第 6~11 天）—— 核心功能

| Task | Est | 说明 |
|------|-----|------|
| T-PRICE-001~004 | 14h | 定价 |
| T-TRADE-001~005 | 19h | 交易 |
| T-NEUT-001~004 | 19h | 中立化主干 |
| **小计** | **52h** | |

**里程碑 M2**：38 个生物不再主动攻击，右键能打开交易界面，价格正确，每日 1 次限制生效。

### Sprint 3（第 12~16 天）—— 特殊适配与仇恨

| Task | Est | 说明 |
|------|-----|------|
| T-NEUT-005~007 | 18h | 10 个特殊适配 |
| T-ANGER-001~004 | 17h | 仇恨全链路 |
| T-TEST-001~004 | 13h | 测试（含 P2 验证） |
| **小计** | **48h** | |

**里程碑 M3**：仇恨语义完全符合三条硬约束，特殊生物行为正确，P2 结论明确。

### Sprint 4（第 17~20 天）—— 发布

| Task | Est | 说明 |
|------|-----|------|
| T-REL-001~005 | 20h | 真机验证 + 文档 + 发布 |
| **小计** | **20h** | |

**里程碑 M4**：v1.0 发布（**待用户确认**）。

---

## 8. 总量估算

| 项 | 数值 |
|----|------|
| 任务数 | 40 |
| 总人时 | **150h** |
| 关键路径 | 62h |
| 按每日 6 有效小时 | 约 **25 个工作日** |

---

## 9. 风险任务标记

| 任务 | 风险 | 缓解 |
|------|------|------|
| T-NEUT-003 | Brain 系每 tick 拦截可能有性能开销 | 先做性能基线，超标改用事件驱动 |
| T-NEUT-005 | 袭击系 3 个共享 `Raider` 基类，改动易互相影响 | 单独分支，逐个真机验证 |
| T-ANGER-003 | 「禁止链式传播」实现易出错 | 加 `alertedBy` 标记 + 单测覆盖传播边界 |
| T-PRICE-001 | 战利品表解析依赖 MC 内部 API | spike 已验证可行，但版本升级需回归 |
| T-TEST-004 | P2 若不成立，需补客户端模组 | 影响发布定位文案，提前到 Sprint 3 |

---

## 10. Owner 分配建议

本项目为单人 + AI agent 协作，按「可委派度」分类：

| 类别 | 任务 | 说明 |
|------|------|------|
| **可完全委派 agent** | T-PRICE-*, T-TEST-001~003, T-CFG-001~002 | 纯逻辑，判据明确，单测可验 |
| **agent 实现 + 人工验证** | T-NEUT-*, T-TRADE-*, T-ANGER-* | 涉及 MC 运行时行为，必须真机验 |
| **需人工决策** | T-REL-002/004/005 | 文案面向玩家、发布时机 |
| **必须人工** | T-REL-005 | 发布动作，用户显式确认 |

---

## 变更记录

| 日期 | 版本 | 作者 | 变更 |
|------|------|------|------|
| 2026-09-11 | v1.0 | Hermes | 初版：40 任务 / 9 Epic / 4 Sprint / 150 人时 |
