# Peace And Love — 项目状态

- **项目 slug**：`peace-and-love`
- **Mod ID**：`peaceandlove`
- **包名**：`top.windyvalley.peaceandlove`
- **许可**：MIT
- **路径**：`D:\Coding\projects\peace-and-love`
- **类型**：Minecraft Java 版 Mod（首发 1.21.1，Fabric + NeoForge）
- **定位**：面向种田/建筑玩家的**和平主义玩法包**（保留血量与饥饿机制，用交易替代战斗获取掉落物）
- **最后更新**：2026-09-11

## 当前阶段（2026-09-11 更新）

**design 阶段已完成**，交付物：

| 文档 | 内容 |
|------|------|
| `02-tech-stack.md` | 8 项选型决策对比表，全部 API 签名经字节码实测 |
| `02-arch-diagram.md` | C4 三层架构图 + 4 张时序图 + 状态机 + 定价曲线 |
| `adr/001-architectury-multiloader.md` | 多加载器方案 |
| `adr/002-merchant-injection.md` | 交易注入（推翻初判，改用方案 A） |
| `adr/003-pricing-and-restock.md` | 对数定价 + 原生次数机制 |
| `adr/004-neutralization-strategy.md` | 双策略中立化 + 生效范围模型 |
| `02-design.md` | 工程结构、四层架构、核心接口、Mixin、数据流、配置、命令、测试清单 |

**design 阶段新增 spike 产物**（`spikes/design-verify/`）：

| 文件 | 结论 |
|------|------|
| `extract_api.py` | `Merchant` 仅 9 方法零字段依赖；`MerchantOffer` 含 uses/maxUses/resetUses |
| `verify_critical_v2.py` | ★ `GoalSelector.removeAllGoals(Predicate)` **存在**，无需反射 |
| `reprice.py` → `final_pricing_128.json` | PRICE_MAX=128 全量重算，**110 条单调性 100% 通过，零撞顶** |
| `adapted_list.py` → `adapted_mobs_v1.json` | v1.0 已适配 38 个（Goal 32 + Brain 6） |

**✅ 凋灵决策已落地**：移出默认白名单 → 默认中立化（`boss_trading_enabled=false` 时不开交易）。默认白名单最终 **6 项**：掠夺者、卫道士、唤魔者、恼鬼、幻翼、潜影贝。
顺带修正末影龙的 `default_whitelisted` 残留标记 —— 不适配、不进白名单，行为完全不变。

---

## P1~P4 验证（2026-09-11 完成 3/4）

详见 `P1-P4-VERIFY.md`。验证工程 `spikes/p1-p3-probe/`（真实 Architectury 三模块，双端构建通过）。

| # | 验证项 | 结论 |
|---|--------|------|
| **P1** | NeoForge 是否需 AT | ✅ **不需要** —— 真实服务端实测 `Merchant.isAssignableFrom(Mob.class)=true`，accesswidener 空 |
| **P2** | 客户端不装模组能否交易 | ⚠️ **未实测** —— 理论成立（`openTradingScreen` 是 default 走原版协议），但需双端联机验证 |
| **P3** | 注入 Mob 基类 vs 38 类 | ✅ **维持基类** —— 82 concrete 子类，额外 44 个，每实例 ~24 B 懒加载，可忽略 |
| **P4** | `NeutralMob` 冲突 | ✅ **无冲突**，但**原假设被推翻** —— 真实交集是末影人 + 僵尸猪灵（Goal 系），非猪灵等 4 个 Brain 系 |

**P4 带出 2 个新特殊适配**（8 → 10）：`EndermanAdapter`（禁用凝视激怒）、`ZombifiedPiglinAdapter`（接管群体报复）。

**自查发现 3 处自身错误并已修正**：`Merchant` 方法数 9→12；P4 原假设错误；P4 v2 漏掉末影人。

**下一步**：Sprint 2 中立化核心（T-NEUT-001~003）。

---

## Dev 阶段 · Sprint 1（2026-09-12 完成）

里程碑 **M1 达成**：服务端能起、命令骨架可用、门控判定正确（但尚无行为变化——中立化未接 Mixin）。

| 任务 | 产出 | 测试 |
|------|------|------|
| T-SETUP-001~003 | 正式工程骨架 + 入口类 + 7 包分层 | — |
| T-CFG-001~004 | PalConfig/ConfigLoader/ConfigManager + /pal 命令骨架 | 30 |
| T-SCOPE-001~003 | AdaptedMobs(38) + 双重门控 + 无效提示 | 26 |
| T-SETUP-004 | CI 工作流（本地验证过，跑绿待推送） | — |

**单测 60 条全绿。** 双端 jar 构建通过。

修正的问题：
- neutralization_plan_v3.json 混入末影龙（33+6=39）→ 剔除后 32+6=38
- 设计文档（/pal）与任务卡（/peaceandlove）命令名不一致 → 统一双注册
- EntityType 测试需 Bootstrap 引导（已记 memory）

移交真机/后续的未测项：
- /pal 命令注册、权限、tab 补全（依赖服务端运行时）
- CI 在 GitHub 实际跑绿（需推送）
- 门控实际效果（待 T-NEUT 挂上 Mixin 后验证）

---

## Decompose 阶段（2026-09-11 完成）

产出：`03-decomposition.md`、`03-task-graph.md`、`tasks/`（40 个任务文件）

| 项 | 数值 |
|----|------|
| Epic | 9 个（SETUP/SCOPE/CFG/PRICE/TRADE/NEUT/ANGER/TEST/REL） |
| 任务 | **40 个** |
| 总人时 | **150h** |
| 关键路径 | 62h |
| Sprint | 4 个（约 25 个工作日） |

### 里程碑

| 里程碑 | 内容 | 验证 |
|--------|------|------|
| **M1** | 服务端可启动，命令可用，门控正确（无行为变化） | 服务端 + 单测 |
| **M2** | 38 生物中立化 + 交易可用 + 价格正确 | **真机** |
| **M3** | 仇恨三条硬约束满足 + 10 特殊适配 + P2 结论 | **真机** |
| **M4** | v1.0 发布 | **须用户确认** |

### 关键安排

- **P2 验证排入 T-TEST-004（Sprint 3）** —— 提前而非放到发布阶段，因其结论影响宣传文案定位
- **T-NEUT-007 为 P4 验证新增** —— 末影人凝视激怒 + 僵尸猪灵群体报复，原设计无此任务
- **T-REL-005 标记 🔒** —— 发布动作须用户显式确认，不得自动执行
- 3 个风险任务已标注缓解方案：T-NEUT-003（性能）、T-NEUT-005（Raider 共享基类）、T-ANGER-003（链式截断）

---

## 历史阶段

| 阶段 | 状态 | 产物 | 完成时间 |
|------|------|------|---------|
| requirements | ✅ **定稿** | `01-requirements.md` v0.3 | 2026-09-11 |
| risk register | ✅ **定稿** | `RISKS.md` v1.3（25 项，高危 0） | 2026-09-11 |
| **spike (R1/R2/R3)** | ✅ **完成** | `SPIKE-REPORT.md` + `spikes/` | 2026-09-11 |
| **design** | ✅ **完成** | `02-design.md` + `02-tech-stack.md` + `02-arch-diagram.md` + `adr/`×4 | 2026-09-11 |
| decompose | ⏳ **可开始** | `03-decomposition.md` + `tasks/` | — |
| dev | ⬜ 未开始 | 代码 + commit | — |
| test-plan | ⬜ 未开始 | `04-test-plan.md` | — |
| automate-test | ⬜ 未开始 | 测试脚本 + CI | — |

## Spike 结论摘要

| Spike | 原风险 | 结论 | 新等级 |
|-------|--------|------|--------|
| **R1** 战利品表定价 | 🔴 H | ✅ 可行。结构可 public 遍历，Mixin 仅 7 个 Accessor；110 条目**单调性 100% 通过** | 🟢 L |
| **R2** 交易能力注入 | 🔴 H | ⚠️ **原判断推翻** → 推荐方案 **A（注入 Merchant）**。补货可直接用 `maxUses=1`+`restock()` | 🟡 M |
| **R3** AI 系统适配 | 🔴 H | ✅ 已量化（v3）：**Goal 32 / Brain 6 / 自有 AI 1 = 39 个全部需实现** | 🟡 M |

**🔴 高风险项：3 → 0**

### spike 中修正的缺陷（算法 4 + 判据 3 + 脚本 2）

| 项 | 缺陷 | 若不修的后果 | 发现方式 |
|----|------|------------|---------|
| R1-① | 线性反比定价 | epk ≤ 0.11 全撞价格上限，稀有度无法区分 | 自查 |
| R1-② | `uniform` count 未 clamp | 凋灵骷髅煤炭被误判零产出 → 定天价 | 自查 |
| R1-③ | `rolls` 当 float 读 | 女巫表直接崩溃 | 自查 |
| R1-④ | 忽略 entry weight | 女巫木棍概率算错 | 自查 |
| R3-① | 把 `customServerAiStep` 当 Brain 标志 | 误判 6 个生物 | 自查 |
| **R3-②** | **「默认在白名单」= 「零工作量」** | **漏算 8 个生物的适配工作** | **★ 用户指出** |
| R3-③ | 二分法「不是 Brain 就是 Goal」 | 误判末影龙（实为第三类自有 AI） | 自查后字节码验证 |
| 脚本-① | `verify_restock.py` 读外层 bundler jar | 【3】【4】节输出空白（原始脚本正确，不影响先前结论） | 自查 |
| 脚本-② | 自写 class 解析器返回 None | 改为复用 `analyze.py` 验证过的实现 | 自查 |

## ✅ 已锁定的决策

| 项 | 决策 |
|---|---|
| **生效范围模型** | **`已适配列表 ∩ 非白名单`** —— 能力边界与管理员策略分离 |
| v1.0 适配范围 | **38 个** —— Goal 32 + Brain 6 |
| 末影龙 | **暂缓至 v1.1**，不进已适配列表，也不进白名单 |
| 监守者 | 已适配，**不进**默认白名单，中立化并可交易 |
| 默认白名单 | 6 项：掠夺者/卫道士/唤魔者/恼鬼/幻翼/潜影贝（均已适配，移出即生效） |
| **仇恨触发源** | **仅玩家攻击**（含玩家投射物/宠物）。NPC 攻击、环境伤害、怪物内斗**不介入** |
| **仇恨目标** | **只锁定攻击者玩家**，不扩散到其他玩家或 NPC |
| **机制边界** | 模组只管中立↔敌对**状态切换**；敌对后行为交回原版 AI，不与原版群体机制叠加 |
| `PRICE_MAX` | 默认 **128**，可配（卡 `MerchantOffer` 双槽 64+64 上限） |
| 定价锚点 | `epk_cheap=2.0` / `epk_rare=0.005` 默认值，可配 |
| 交易频次 | `max_uses_per_day=1` + `restock_interval_days=1`，均可配 |
| 绿宝石平衡基准 | 按**无绿宝石农场**测算 |

## 架构已可确定

```
Architectury（common / fabric / neoforge）
  + 方案 A：Mixin 注入 Merchant 接口，复用原版 MerchantMenu
  + 生效判定：AdaptedMobRegistry（代码常量） ∩ !whitelist（配置）
  + NeutralizationStrategy 两实现（v1.0）：
        GoalBasedStrategy    (32 个)
        BrainBasedStrategy   (6 个)
      ⏸ CustomAiStrategy    (末影龙，v1.1 再评估)
  + 仇恨切换：仅 hurt 来源可归因玩家时触发；复用原版 NeutralMob
  + LootPriceProvider 接口隔离版本差异（为 1.21.8/1.21.11 留位）
  + 交易次数：MerchantOffer.maxUses=1 + 自实现 resetAllUses() 每日补货
```

原先「spike 结论可能推翻架构」的担忧**已解除**——方案 A 成本远低于预估，不需要两套源码树。

## 🙋 仍待 design 阶段决策

- [ ] `boss_trading_enabled` 默认值（建议 false，影响凋灵）
- [ ] 交易触发方式：普通右键 vs 潜行右键
- [ ] 是否需要视觉提示区分中立/敌对
- [ ] 1.21.8 / 1.21.11 首发就带还是后补

## design 阶段待做的最小原型验证

| # | 验证项 | 原因 |
|---|--------|------|
| P1 | NeoForge Mixin 接口注入是否需要 Access Transformer | 方案 A 唯一残留不确定性 |
| P2 | 客户端不装模组能否交易 | 若能则是卖点，也决定 R25 |
| P3 | 注入 `Mob` 基类 vs 38 个已适配目标类 | 影响面 vs 代码量权衡 |

## 已解决的 Blockers

| # | 原阻塞项 | 决策 |
|---|---------|------|
| ~~B1~~ | MC 版本未收敛 | ✅ 放弃 1.20.x，首发 1.21.1 |
| ~~B2~~ | 示警扩散语义 | ✅ 同 EntityType / 球形 4 格 / 单层不链式 |
| ~~B3~~ | 白名单默认值 | ✅ 掠夺者/卫道士/唤魔者/恼鬼/幻翼/潜影贝 |
| ~~B4~~ | 敌对是否可逆 | ✅ 可逆（默认 30 秒冷却） |
| ~~B5~~ | 交易上限策略 | ✅ 单次产出=最大掉落数 / 每游戏日补货 |
| ~~B6~~ | 本机缺 JDK 17 | ✅ 已消除（放弃 1.20.x 后不需要） |

## 关键版本锁定（已实测凭证）

| 组件 | 版本 |
|------|------|
| MC 首发 | 1.21.1 |
| Fabric Loader | 0.19.5 |
| Fabric API | 0.116.17+1.21.1 |
| NeoForge | 21.1.250 |
| Architectury API | 13.0.11 (+fabric / +neoforge) |
| Architectury Loom | 1.11.454 |
| Stonecutter | 0.9.8 |
| JDK | Zulu 21（`~/scoop/apps/zulufx21-jdk`） |

## Handoff

```
From: spike (Hermes)
To:   design (unassigned)
What: 用户裁定 4 个问题后，产出：
      • 02-design.md —— 模块划分、类图、数据流
      • adr/001-multiloader.md —— Architectury 选型
      • adr/002-trade-injection.md —— 方案 A（含 spike 证据）
      • adr/003-pricing-algorithm.md —— 对数曲线 + 4 个缺陷的修正记录
      • adr/004-neutralization-strategy.md —— Goal/Brain 双策略
      并完成 P1~P3 最小原型验证
证据基础：SPIKE-REPORT.md + spikes/r3-ai/neutralization_plan.json
```
