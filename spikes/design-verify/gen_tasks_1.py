"""
批量生成 03-tasks/ 下的任务文件
==================================
按 eng-decompose skill 的模板生成 40 个任务文件。
详细内容（验收标准/技术要点）针对每个任务单独编写，非套模板。
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent.parent / "03-tasks"
OUT.mkdir(exist_ok=True)

TPL = """# {tid}: {title}

**状态：** todo
**优先级：** {prio}
**预估：** {est}
**Owner：** {owner}
**依赖：** {deps}
**可并行：** {para}

## 目标

{goal}

## 来源

{src}

## 验收标准

{accept}

## 技术要点

{tech}

## 产出物

{output}

## 备注

{note}
"""

T = []


def add(tid, title, prio, est, owner, deps, para, goal, src, accept, tech, output, note="无"):
    T.append(dict(tid=tid, title=title, prio=prio, est=est, owner=owner,
                  deps=deps, para=para, goal=goal, src=src,
                  accept=accept, tech=tech, output=output, note=note))


# ─────────────── SETUP ───────────────
add("T-SETUP-001", "由探针工程演进为正式工程", "P0", "3h", "agent",
    "无", "无",
    "把 `spikes/p1-p3-probe/` 提升为项目根工程，清理探针专用代码，保留全部已验证的 Gradle 配置。",
    "- 设计：`02-design.md` §1 工程结构\n- 验证：`P1-P4-VERIFY.md`（探针工程构建已通过）",
    """- [ ] 根目录出现 `build.gradle` / `settings.gradle` / `gradle.properties` / `gradlew`
- [ ] `mod_version` 改为 `1.0.0`，移除 `-probe` 后缀
- [ ] 删除 `ProbeCommon.java` / `ProbeResults.java` / `*ProbeMixin.java` / `read_probe.py`
- [ ] `./gradlew build` 双端通过
- [ ] 产出 `fabric/build/libs/*.jar` 与 `neoforge/build/libs/*.jar`""",
    """**必须原样保留以下已验证配置（改动会导致构建失败）：**
- Gradle **8.10.2** wrapper —— Gradle 9.x 与 Loom 1.7 不兼容
- `fabric/gradle.properties` 写 `loom.platform=fabric`
- `neoforge/gradle.properties` 写 `loom.platform=neoforge`
- `common/src/main/resources/peaceandlove.accesswidener` 保留（空文件即可，P1 已证明无需 AT）
- `architectury_api_version=13.0.11` / `neoforge_version=21.1.250` / `fabric_loader_version=0.16.9`

**Mixin 包纪律**：工具类不得放在 `top.windyvalley.peaceandlove.mixin` 包内，
否则抛 `IllegalClassLoadError: ... cannot be referenced directly`。""",
    "- 代码：项目根全部 Gradle 文件 + `common/fabric/neoforge` 三模块\n- 测试：无\n- Commit：`chore: 由 spike 探针工程演进为正式工程骨架`",
    "探针工程留在 `spikes/p1-p3-probe/` 不动，作为验证证据归档。")

add("T-SETUP-002", "Git 仓库初始化", "P0", "1h", "agent",
    "T-SETUP-001", "T-SETUP-003",
    "初始化 git 仓库，配置 .gitignore，完成首次提交。",
    "- 用户偏好：分批次提交，CHANGELOG 风格中文 commit message",
    """- [ ] `git init` 且默认分支为 `main`
- [ ] `.gitignore` 覆盖 `build/` `.gradle/` `run/` `*.log` `.idea/`
- [ ] `spikes/` 下的 jar 与 mappings 大文件被忽略（`server-*.jar` / `server_mappings.txt`）
- [ ] 首次提交成功，`git status` 干净""",
    """- 大文件确认：`server-1.21.1.jar` 约 50 MB，`server_mappings.txt` 约 8 MB，**必须忽略**
- spike 的分析脚本与 JSON 结论要保留入库（体积小、是决策依据）""",
    "- 代码：`.gitignore`\n- Commit：`chore: 初始化 git 仓库`")

add("T-SETUP-003", "包结构与分层骨架", "P0", "2h", "agent",
    "T-SETUP-001", "T-SETUP-002",
    "按设计创建 7 个模块的包结构与空类骨架，建立分层依赖规则。",
    "- 设计：`02-design.md` §1 工程结构、§2 分层与依赖规则",
    """- [ ] 创建 `config/` `scope/` `pricing/` `trade/` `neutralize/` `anger/` `mixin/` 七个包
- [ ] 每个包有 `package-info.java` 说明职责与依赖方向
- [ ] `PeaceAndLove.java` 入口类可被两端初始化器调用
- [ ] 编译通过""",
    """分层依赖规则（不得反向依赖）：
```
mixin → (trade, neutralize, anger) → scope → config
pricing → (独立，仅依赖 config)
```
`scope` 不得依赖 `trade`/`neutralize`，否则形成环。""",
    "- 代码：`common/src/main/java/top/windyvalley/peaceandlove/**`\n- Commit：`feat: 建立分层包结构骨架`")

add("T-SETUP-004", "GitHub Actions 双端构建 CI", "P1", "3h", "agent",
    "T-SETUP-002", "T-CFG-001",
    "配置 CI，push 与 PR 时自动构建双端 jar 并跑单测。",
    "- 需求：`01-requirements.md` §4 非功能需求",
    """- [ ] `.github/workflows/build.yml` 存在
- [ ] JDK 21 (temurin)，Gradle 缓存启用
- [ ] `./gradlew build` 双端通过
- [ ] 产物上传为 artifact
- [ ] CI 在 GitHub 上实际跑绿一次""",
    "- 注意 Gradle wrapper 校验（`gradle/wrapper/gradle-wrapper.jar` 需入库）\n- 用 `actions/setup-java@v4` + `gradle/actions/setup-gradle@v4`",
    "- 代码：`.github/workflows/build.yml`\n- Commit：`ci: 添加双端构建工作流`")

# ─────────────── SCOPE ───────────────
add("T-SCOPE-001", "AdaptedMobs 38 个常量", "P0", "3h", "agent",
    "T-SETUP-003", "T-CFG-001",
    "定义 v1.0 已适配的 38 个生物常量，按 Goal(32)/Brain(6) 分组，不可变。",
    "- 设计：`02-design.md` §3.2 已适配生物列表\n- 数据：`spikes/r3-ai/neutralization_plan_v3.json`",
    """- [ ] `AdaptedMobs.GOAL_BASED` 含 32 个 EntityType
- [ ] `AdaptedMobs.BRAIN_BASED` 含 6 个：猪灵/猪灵蛮兵/疣猪兽/僵尸疣猪兽/监守者/旋风人
- [ ] 合计 38，且 `isAdapted(EntityType)` 查询为 O(1)
- [ ] **末影龙不在列表中**
- [ ] 集合为不可变（`Set.copyOf` 或 `ImmutableSet`）
- [ ] 单测断言总数 == 38""",
    """从 `neutralization_plan_v3.json` 生成，**不要手敲**，避免拼写错误。
注意类名与 entity id 不一致的特例：`WitherBoss`→`wither`、`EnderMan`→`enderman`。""",
    "- 代码：`scope/AdaptedMobs.java`\n- 测试：`AdaptedMobsTest.java`\n- Commit：`feat(scope): 定义 38 个已适配生物常量`")

add("T-SCOPE-002", "NeutralizationScope 门控判定", "P0", "3h", "agent",
    "T-SCOPE-001, T-CFG-001", "T-PRICE-001",
    "实现「已适配列表 ∩ 非白名单」双重决策门控，这是全项目的行为总开关。",
    "- 设计：`02-design.md` §3.1 生效范围判定\n- 决策：`02-adr/004`\n- 需求：FR-1.5",
    """- [ ] `isNeutralized(type) == isAdapted(type) && !inWhitelist(type)`
- [ ] `canTrade(type) == isNeutralized(type) && tradingEnabled && (非Boss || bossTradingEnabled)`
- [ ] 第三方 Mod 生物一律返回 false（不在已适配列表）
- [ ] 白名单变更后立即生效（读配置当前值，不缓存）
- [ ] 单测覆盖真值表全部 4 种组合""",
    """**这是全项目最关键的判定**，务必先写单测再实现。

真值表：
| 已适配 | 在白名单 | 结果 |
|--------|---------|------|
| ✅ | ❌ | **中立化** |
| ✅ | ✅ | 保持原版 |
| ❌ | ❌ | 保持原版 |
| ❌ | ✅ | 保持原版（配置无效，打 INFO） |""",
    "- 代码：`scope/NeutralizationScope.java`\n- 测试：`NeutralizationScopeTest.java`\n- Commit：`feat(scope): 实现双重决策门控`")

add("T-SCOPE-003", "未适配生物的 INFO 日志提示", "P2", "1h", "agent",
    "T-SCOPE-002", "无",
    "管理员把未适配生物（如末影龙）加入白名单时，打 INFO 日志说明该配置无效。",
    "- 设计：`02-design.md` §10 凋灵的处理",
    """- [ ] 加载配置时检测白名单中的未适配 id
- [ ] 打 INFO（非 WARN，这不是错误）
- [ ] 日志文案说明「该生物 v1.0 未适配，配置不生效，行为与原版一致」
- [ ] 每次 reload 只打一次，不刷屏""",
    "用 `Set<String>` 去重已提示过的 id，reload 时清空。",
    "- 代码：`scope/NeutralizationScope.java`\n- Commit：`feat(scope): 未适配生物配置给出 INFO 提示`")

# ─────────────── CFG ───────────────
add("T-CFG-001", "PalConfig 数据类与默认值", "P0", "3h", "agent",
    "T-SETUP-003", "T-SCOPE-001",
    "定义配置数据类，含全部字段与默认值（特别是 6 项默认白名单）。",
    "- 设计：`02-design.md` §6 配置文件设计\n- 需求：FR-3.1",
    """- [ ] 默认白名单**恰好 6 项**：掠夺者/卫道士/唤魔者/恼鬼/幻翼/潜影贝
- [ ] **凋灵与监守者不在默认白名单**
- [ ] `price_max=128`、`epk_cheap=2.0`、`epk_rare=0.005`
- [ ] `restock_interval_days=1.0`、`anger_cooldown_seconds=30`、`kin_alert_radius=4.0`
- [ ] `trading_enabled=true`、`boss_trading_enabled=false`
- [ ] 单测断言默认白名单 size == 6""",
    "用 record 或不可变类；字段名与 JSON key 完全一致，便于序列化。",
    "- 代码：`config/PalConfig.java`\n- 测试：`PalConfigDefaultsTest.java`\n- Commit：`feat(config): 定义配置数据类与默认值`")

add("T-CFG-002", "配置 JSON 读写与容错", "P0", "4h", "agent",
    "T-CFG-001", "T-PRICE-001",
    "实现配置文件的加载、保存、校验；损坏或缺字段时回退默认值并告警。",
    "- 设计：`02-design.md` §6\n- 需求：FR-3.1",
    """- [ ] 首次启动自动生成 `config/peaceandlove.json`
- [ ] 字段缺失时用默认值补齐并回写
- [ ] JSON 语法错误时**不崩服**，回退全默认 + WARN 日志
- [ ] 数值越界时 clamp 并 WARN（如 price_max < 1）
- [ ] 未知字段保留不丢弃（向前兼容）""",
    "用 GSON（MC 自带）。注意 `price_max` 上限受 `MerchantOffer` 双槽限制，最大 128。",
    "- 代码：`config/ConfigLoader.java`\n- 测试：`ConfigLoaderTest.java`（含损坏 JSON 用例）\n- Commit：`feat(config): 实现配置读写与容错`")

add("T-CFG-003", "/peaceandlove reload 热重载命令", "P0", "3h", "agent",
    "T-CFG-002", "T-PRICE-002",
    "实现配置热重载命令，重载后门控与定价立即生效，无需重启。",
    "- 设计：`02-design.md` §7 命令设计\n- 需求：FR-3.2",
    """- [ ] `/peaceandlove reload` 需 OP 权限（level 2）
- [ ] 重载后白名单变更立即影响已加载实体（调用 neutralize/restore）
- [ ] 重载后定价表重建
- [ ] 返回反馈消息含变更摘要
- [ ] 重载失败时保留旧配置，不进入半初始化状态""",
    """**关键**：重载时白名单移入的生物要 `restore()`，移出的要 `neutralize()`，
需遍历已加载实体。依赖 T-NEUT-004 的可逆能力，若尚未完成可先只改判定、实体下次 tick 生效。""",
    "- 代码：`config/ConfigCommand.java`\n- Commit：`feat(config): 实现 reload 热重载命令`")

add("T-CFG-004", "/peaceandlove whitelist 命令族", "P0", "4h", "agent",
    "T-CFG-003", "无",
    "实现白名单的增删查命令，变更后持久化并立即生效。",
    "- 设计：`02-design.md` §7\n- 需求：FR-3.2",
    """- [ ] `whitelist list` 列出当前白名单（含中文名）
- [ ] `whitelist add <id>` / `remove <id>` 支持 tab 补全
- [ ] 补全候选来自**已适配列表**，避免输入无效 id
- [ ] 变更后自动保存配置文件
- [ ] 对未适配 id（如末影龙）给出 INFO 提示但仍允许添加
- [ ] 变更立即影响已加载实体""",
    "用 `SuggestionProvider` 提供补全；id 支持带/不带 `minecraft:` 前缀。",
    "- 代码：`config/ConfigCommand.java`\n- Commit：`feat(config): 实现白名单管理命令`")

for t in T:
    (OUT / f"{t['tid']}.md").write_text(TPL.format(**t), encoding="utf-8")

print(f"已生成 {len(T)} 个任务文件 -> {OUT}")
for t in T:
    print(f"  {t['tid']}.md")
