# Peace And Love — 项目状态

- **项目 slug**：`peace-and-love`
- **Mod ID**：`peaceandlove`
- **包名**：`top.windyvalley.peaceandlove`
- **许可**：MIT
- **路径**：`D:\Coding\projects\peace-and-love`
- **类型**：Minecraft Java 版 Mod（首发 1.21.1，Fabric + NeoForge）
- **定位**：面向种田/建筑玩家的**和平主义玩法包**（保留血量与饥饿机制，用交易替代战斗获取掉落物）

- **最后更新**：2026-10-12

---

## 当前阶段（2026-10-12 更新）：交易系统 Sprint —— 定价域全绿，交易组装器完成，下一步右键开 GUI（heavy）

**分支**：`feat/trade-system`（功能演进不在 main，未开 PR）。**叶子任务进度 27/44（61%）**。common 单测 **165 全绿（0 skip）**。

### 本轮完成（定价域 PRICE 全部 done + 交易组装器）

| 任务 | 产出 | commit | 验证 |
|------|------|--------|------|
| T-PRICE-001 | 真实掉落物扫描器 `LootTableScanner`（替代手填，直接读原版战利品表，Bootstrap 引导） | 已 push | 单测 + 真机 70 条与黄金基线逐条等值 |
| T-PRICE-002.1 | `PricingEngine`（对数曲线 + override + clamp 1..128）+ 规则文档 `PRICING_RULES.md` | 已 push | 单测（价格纯函数） |
| T-PRICE-002.2 | `ConfigurablePriceCurve` 配置绑定层 + loader 锚点关系校验（cheap≥rare，否则启动失败） | `84467ec` | 14 单测 |
| T-PRICE-003 | `PriceTable` 不可变构表/缓存 + `PriceTableService`（启动构表、`/pal trade reload` 重建） | 已 push | 9 单测 + **真机 PASS** |
| T-PRICE-004 | `selfCheck` 单调性/撞限自检 + 启动 INFO / 逆序 WARN（不阻断启动） | `48b565a` | 5 单测 + **真机 PASS** |
| T-TRADE-002.1 | `TradeSpec`（单条规格 → 原版 `MerchantOffer`，绿宝石双槽拆分） | 已 push | 单测 |
| T-TRADE-002.2 | `TradeOfferBuilder.assemble(type,config,table)` 门控+遍历定价表组装，接入 `MobMerchantMixin.getOffers()` | `c195627` | 7 单测，**3/4 验收（第 4 条留 003 真机）** |

**真机结论（测试服 192.0.2.10，NeoForge 1.21.1）**：
- 构表 70 条报价（38 适配生物域内）与黄金基线 `final_pricing_128.json`（已按扫描域过滤）**逐条 item/epk/price/amount 等值**；override 正/负、白名单守卫、签名守卫（reload 不改锚点）均验过。
- 默认自检：`共 70 条，撞下限 3、撞上限 0`（INFO），无逆序，不阻断启动；把僵尸村民腐肉 override 填成 120 立即 WARN 检出 3 对逆序并列定位串。
- 测试服当前跑的就是最新源码构建（verify 开关、逐 zip 条目 CRC32 核对一致），配置已还原默认、保持开机；旧 jar 备份在远端 `mods_backup/`。

**本轮修掉的真 bug**：reload 回执骗人——`PalConfig.summarize()` 漏了锚点/override/仇恨/限购字段，改锚点仍显示「无变更」（`a2288e8`，真机复验回执正确）。

### 交接给新会话（cold start 必读）

- **下一个任务：T-TRADE-003 —— 右键中立怪物打开原版交易 GUI**。这是把整条链（扫描→定价→组装→界面）在游戏里点亮的关键，也是 **heavy 节点**：要给 `MobMerchantMixin` 注入 `mobInteract`（服务端 `MerchantMenu` + 网络同步），不是纯逻辑。
- **验证方式变了**：测试服是**无客户端 dedicated server**，「右键→看到绿宝石价→成交」这类交互 RCON/RPC 验不了。须用 **runClient 真机客户端自动化**（独立仓 `WindyValley/mc-client-rpc`，真实按键映射驱动；PAL 业务脚本放本仓 `tests/automation/`，通用驱动留 mc-client-rpc）。内存里有连服/召唤/采样/读日志要写进一个 .py 跑一条命令的纪律。
- **003 会一并收口的旧账**：① T-TRADE-002.2 **验收 4**（mixin 织入后游戏内真能取价/显示）；② T-TEST-001 交易链真机；③ T-NEUT-004 里标「待交易链接线」的右键项；④ reload 后已存在生物的报价刷新（目前 `pal$offers` 懒缓存一次，锚点 reload 后旧生物不刷新，003/补货时处理）。
- **已测路径**：定价扫描/曲线/构表/组装/门控/自检全链路单测 + 服务端真机（日志/RPC 可读项）。**未测路径（必须真机客户端）**：右键打开 GUI、绿宝石报价在界面显示、双槽支付成交、maxUses 买光与补货、P2「客户端不装模组能否交易」。
- **关键类**：`pricing/LootTableScanner`、`pricing/PricingEngine`+`ConfigurablePriceCurve`、`pricing/PriceTable`+`PriceTableService`、`trade/TradeSpec`、`trade/TradeOfferBuilder`、`mixin/MobMerchantMixin`（已有 Merchant 接口注入 + 空的 notifyTrade/overrideXp，右键注入待加）。
- **构建开关坑**：`:common:test` 加 `--configure-on-demand` 可跳 fabric 配置；但 `:neoforge:build` 出 jar **不能**加它（报 accessWidenerPath is final），去掉即可。部署 jar 必须 `-PenableVerifyRpc=true`，否则 BuildFlags 常量折叠、产物无 RPC 且对不上。
- **工程改进**：任务脚本 `task.py` 已补 `check/uncheck <序号>` 子命令（支持「已写未验」部分勾选，别再手改 checkbox）。
- 发布（T-REL-005）🔒 须用户显式说「发」；仓库保持私有。

---

## 当前阶段（2026-09-25 更新）：中立化 / 愤怒 / 示警全链路完成

**版本**：0.0.2（SemVer，正式发布前不使用 1.0.0）。仓库私有；0.0.2 以 GitHub 预发布 Alpha 形式发布。

### 本阶段核心成果

**1. Brain 系中立化重构——从「每 tick 擦记忆」改为「写入源头拦截」。**

旧方案每 tick 全服遍历怪、清攻击记忆，既耗性能又有探针漏接导致被打无法反击的隐患。现改为：

- 字节码确认所有记忆写入汇聚到包私有方法 `setMemoryInternal`（无传感器旁路、无反射直改 Map），用 Mixin 在该方法 HEAD 设一道门控 {@code BrainAttackGate}；
- 门控条件：攻击类记忆（`ATTACK_TARGET`，猪灵系另含 `ANGRY_AT`）+ 已中立化 + 当前非愤怒 → 取消写入；玩家攻击后愤怒已记录，门控读到「愤怒中」即放行反击；清空（eraseMemory）一律放行。
- 旧的每 tick 擦除、愤怒探针、对应事件钩子整体删除。

**2. Brain 系补齐同族示警语义（对齐 Goal 系 A/B/C）。**

新增 `BrainKinAlerter`：玩家打一只 Brain 怪后，半径内同族中立怪标 `KIN_ALERT`（门控本就认此放行）并写入 `ATTACK_TARGET=攻击者`（猪灵系再写 `ANGRY_AT`），单层不级联。

**3. 配套修复：**

- `calmDown` 脱战除了 `setTarget(null)`，补擦 Brain 的 `ATTACK_TARGET/ANGRY_AT`，否则脱战后仍追击；
- **「最后攻击玩家 UUID」兜底**：玩家跑远、目标不可达时原版会自清攻击记忆，导致距离脱战判定找不到玩家；mod 侧记录最后攻击者，据此找回玩家算距离，calmDown 清除；
- 验证探针 `mob.anger` 改为遍历**所有维度**（原来写死主世界，地狱怪查不到），`getTarget` 为空时回退读 Brain 攻击记忆。

### 真机验证（真客户端 + 专用服务器，非单测）

Brain 系 6 种全部**双向**通过：

| 怪 | 平时贴近 | 玩家先攻击 |
|----|---------|-----------|
| 猪灵 piglin | 不掉血 | 反击（HP→0）|
| 猪灵蛮兵 piglin_brute | 不掉血 | 反击（HP→0）|
| 疣猪兽 hoglin | 不掉血 | 反击（HP 20→2.3）|
| 僵尸疣猪兽 zoglin | 不掉血 | 反击 |
| 监守者 warden | 不掉血 | 反击（HP 17.8→0）|
| 旋风人 breeze | 不被射（HP 恒 20）| 反击射击（HP 持续下降）|

同族示警两轮（猪灵 / 疣猪兽）：同族定向 `KIN_ALERT`、异族不示警、二圈单层不级联、跑远脱战后 Brain 记忆全擦回中立——全绿。

> 认知更正：早期「监守者 14s 不掉血=通过」判据偏弱（dump NBT 发现那只是原版愤怒低于攻击阈值）；最终以「攻击命中→服务端 HP 下降→玩家被反击」双向对照为准。

### 分支（功能演进均不在 main 上，未开 PR）

- `feat/brain-memory-source-gate`（已推 origin）：Brain 源头拦截 + 愤怒 + 示警，本阶段主线；
- `chore/automation-test-scripts`（已推 origin）：真机测试脚本归位 `tests/automation/`；
- `main`：干净，跟踪 `origin/main`。

### 测试工具独立成仓

真机自动化驱动（客户端 JSON-RPC、RCON、启停/部署脚本）独立为 **mc-client-rpc**（私有，`WindyValley/mc-client-rpc`）：

- `feat/real-key-input`（已推）：移动/跳跃改为驱动**真实按键映射**（`options.keyUp/Down/Left/Right/Jump` 的 setDown），由原版 tick 自然驱动并发包；实测移动约 4.5 格/秒；
- PAL 业务验证脚本不放在该仓（已迁回 PAL `tests/automation/`），通用驱动（`combat_loop_test.py`、`rcon.py`）留在该仓作单一来源。

### 下一步（按优先级）

1. **交易系统**：`trade/` 目前仅 package-info，零实现（Mixin 向 Mob 注入原版 Merchant，复用原版交易 GUI；spike 已验证可行）；
2. **定价系统**：`pricing/` 仅 package-info（对数曲线 + 110 掉落物价格，spike 已算好待落地）；
3. 末影龙（第三类自有 AI）暂缓；发布须用户显式确认。

---

## 历史阶段：Design（2026-09-11）

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
- ~~CI 在 GitHub 实际跑绿（需推送）~~ ✅ 已完成（见下）
- 门控实际效果（待 T-NEUT 挂上 Mixin 后验证）

---

## GitHub 仓库与 CI（2026-09-12）

- 仓库：`https://github.com/WindyValley/peace-and-love`（**私有**，release 时再解禁）
- 远程：`origin`，主分支 `main`
- git 代理已配 `http://127.0.0.1:1080`

CI 两次跑绿：
| run | 耗时 | 结论 | 说明 |
|-----|------|------|------|
| 34698848293 | 5m16s | ✅ | 首次。双端 jar + 60 单测全过，产物 178KB |
| 34699189537 | 2m16s | ✅ | 缓存生效。setup-java v4→v5 消除弃用警告 |

残留警告：checkout/upload-artifact/setup-gradle 目标 Node 20 被强制升 24，
属 action 官方未迁移，GitHub 自动兼容，不影响构建。

---

## Dev 阶段 · Sprint 2 进行中（2026-09-14 反击链验证）

**T-NEUT-002 完成（Goal 系中立化策略）**，真机验证反击链生效：

- **真 bug 修复**（`b9c262b`）：原设计「删除攻击 Goal」导致被打不反击。
  根因——`HurtByTargetGoal.mustReach=true`，`canAttack()` 内部 `canReach()`
  依赖 navigation，攻击 Goal 被删后 navigation 未激活 → `canUse()` 永 false。
  修法：参考末影人/北极熊/熊猫原版实现，**保留攻击 Goal、只删主动索敌 Goal**。
- **验证设施**（`2de1789`）：服务端 JSON-RPC（TCP 25585）+ runClient 离线直连。
  真实玩家 Dev（生存）上线，`player.attack` 打僵尸 → 日志 `Dev was slain by Zombie`，
  僵尸持续追击致死，反击链完整工作。

**已测路径**：真实玩家（生存）真实 `playerAttack` 伤害 → 僵尸反击致死。
**未测路径**：骷髅/蜘蛛/苦力怕反击（同策略，建议真机复核）；Brain 系（`BrainBasedStrategy`，不同机制）；玩家输入驱动的完整攻击动作（服务端 RPC 只伪造伤害来源，不模拟输入）。

**遗留**：
- 服务端 JSON-RPC 硬编码开启、无鉴权 → 正式发布前必须关闭/移除（代码已标 TODO）
- 客户端侧 JSON-RPC（真实输入驱动）→ 另立独立项目
- PrismLauncher 实例 `1.21.1-modded` 曾排查：元数据缓存损坏已清（meta/net.neoforged/index.json、net.minecraft/1.21.1.json），客户端 mmc-pack.json 的 NeoForge 被改为 21.1.250（.bak 备份在同目录）

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
