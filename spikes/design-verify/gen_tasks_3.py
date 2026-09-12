"""
批量生成 03-tasks/ 第三批：ANGER / TEST / REL
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


# ─────────────── ANGER ───────────────
add("T-ANGER-001", "LivingEntityHurtMixin 仇恨注入点", "P0", "4h", "agent",
    "T-NEUT-001", "T-TRADE-003",
    "在受伤事件注入，**只有玩家攻击**才触发仇恨，其余伤害源一律不介入。",
    "- 设计：`02-design.md` §4.2 仇恨触发点\n- 需求：FR-1.2（用户两次强调的硬约束）",
    """- [ ] 注入 `LivingEntity#hurt(DamageSource, float)`
- [ ] **玩家直接攻击** → 触发仇恨
- [ ] **玩家投射物**（箭/雪球/三叉戟等）→ 触发仇恨
- [ ] **玩家点燃的 TNT / 苦力怕爆炸** → 触发仇恨（爆炸源可追溯到玩家时）
- [ ] **玩家的宠物**（owner 为玩家的狼/猫等）→ 触发仇恨
- [ ] ❌ 铁傀儡攻击 → **不触发**
- [ ] ❌ 村民卫兵攻击 → **不触发**
- [ ] ❌ 其他怪物攻击（怪物内斗）→ **不触发**
- [ ] ❌ 环境伤害（跌落/岩浆/窒息/仙人掌）→ **不触发**
- [ ] 单测覆盖上述 9 种情况""",
    """**这是全项目语义最敏感的判定**，用户两次强调，务必逐条落实。

伤害源溯源：
```java
Entity direct = source.getDirectEntity();   // 箭
Entity attacker = source.getEntity();       // 射箭的玩家
```

判定链：
1. `attacker instanceof Player` → ✅
2. `attacker instanceof TamableAnimal t && t.getOwner() instanceof Player` → ✅
3. `attacker instanceof PrimedTnt tnt && tnt.getOwner() instanceof Player` → ✅
4. 其余 → ❌ 完全不介入，走原版逻辑

`Entity.hurt(DamageSource,float)` 1.21.1 混淆名为 `a`（spike 已确认）。""",
    "- 代码：`mixin/LivingEntityHurtMixin.java`\n- 测试：`HurtSourceTest.java`（9 种伤害源）\n- Commit：`feat(anger): 实现仇恨触发点（仅玩家攻击）`",
    "⚠️ 用户明确强调过两次的硬约束，实现后必须逐条真机验证。")

add("T-ANGER-002", "AngerController 状态机与单目标锁定", "P0", "5h", "agent",
    "T-ANGER-001", "T-NEUT-004",
    "实现仇恨状态机，仇恨**锁定攻击者本人**，不扩散到其他玩家或 NPC。",
    "- 设计：`02-design.md` §3.6 仇恨控制\n- 需求：FR-1.2",
    """- [ ] 仇恨目标为**单个 UUID**（攻击者本人）
- [ ] 玩家 A 攻击 → 生物只追 A，**不攻击旁边的玩家 B**
- [ ] 仇恨期间不开交易界面
- [ ] 仇恨期间恢复原版攻击 Goal（能反击）
- [ ] 脱战后清除仇恨，恢复中立可交易
- [ ] 多人场景：A 交易中 B 攻击 → 强制关闭 A 的界面并**退回绿宝石**
- [ ] 状态持久化到 NBT（重登不丢仇恨）""",
    """复用原版 `NeutralMob.persistentAngerTarget`（单个 UUID，语义天然吻合）。
末影人与僵尸猪灵已实现该接口的 5 个方法，**可直接复用存储层**。

⚠️ **绿宝石退回**：玩家 A 正在交易界面中，B 攻击导致生物转敌对，
服务端强制关闭 A 的 `MerchantMenu`，此时 A 放在输入槽的绿宝石必须退回背包，
否则物品丢失。用 `MerchantMenu#removed()` 的原版逻辑处理。""",
    "- 代码：`anger/AngerController.java`\n- 测试：`AngerControllerTest.java`\n- Commit：`feat(anger): 实现仇恨状态机与单目标锁定`")

add("T-ANGER-003", "KinAlerter 同族示警", "P0", "5h", "agent",
    "T-ANGER-002", "T-ANGER-004",
    "被玩家攻击时，通知**同一 EntityType**、**球形 4 格内**的同类，且**禁止链式传播**。",
    "- 设计：`02-design.md` §3.6\n- 需求：FR-1.2",
    """- [ ] 半径 `kin_alert_radius=4.0`（可配置），**球形**非立方体
- [ ] 仅同一 `EntityType` 被通知（僵尸不通知骷髅）
- [ ] 被通知者仇恨目标 = **同一个攻击者**（非通知者）
- [ ] ❌ **禁止链式传播**：被通知者不再通知它的邻居
- [ ] NPC 攻击导致的受伤**不触发示警**
- [ ] 半径设为 0 时完全禁用示警
- [ ] 单测覆盖传播边界（4.0 格内/外、链式截断）
- [ ] 真机验证：攻击僵尸群中一只，确认只有 4 格内被激怒且不扩散""",
    """⚠️ **风险任务**：「禁止链式传播」实现易出错。

实现方式：示警调用带 `boolean propagate` 参数
```java
void alert(Mob source, Player attacker, boolean propagate) {
    if (!propagate) return;              // 被通知者不再传播
    for (Mob kin : nearbyKin(source, radius)) {
        kin.setAnger(attacker);
        alert(kin, attacker, false);     // ★ 传 false，截断链式
    }
}
```

球形判定用 `distanceToSqr() <= radius*radius`，
不要用 `AABB.inflate()`（那是立方体，角上会多出 ~73% 体积）。

⚠️ 僵尸猪灵需先禁用原版群体报复（T-NEUT-007），否则双份传播。""",
    "- 代码：`anger/KinAlerter.java`\n- 测试：`KinAlerterTest.java`\n- Commit：`feat(anger): 实现同族示警（单层非链式）`",
    "⚠️ 风险任务：链式截断逻辑需单测重点覆盖。")

add("T-ANGER-004", "脱战冷却恢复中立", "P0", "3h", "agent",
    "T-ANGER-002", "T-ANGER-003",
    "仇恨 30 秒后或玩家脱离 32 格后，生物恢复中立可交易。",
    "- 设计：`02-design.md` §3.6\n- 需求：FR-1.2",
    """- [ ] `anger_cooldown_seconds=30` 后自动脱战
- [ ] `anger_cooldown_seconds=0` 表示**永久仇恨**（不自动脱战）
- [ ] 玩家脱离 32 格后也恢复中立
- [ ] 冷却期间玩家再次攻击 → 重置计时
- [ ] 脱战后交易界面可正常打开
- [ ] 脱战后攻击 Goal 被重新移除（回到中立状态）""",
    """计时基于 tick（30s = 600 tick），存在实体 NBT。

脱战条件（满足其一）：
1. `angerTime <= 0`（冷却结束）
2. `distanceToSqr(target) > 32*32`（脱离距离）

注意：脱战后要重新调用 `neutralize()` 移除攻击 Goal，
否则生物保持敌对行为但状态标记为中立，出现不一致。""",
    "- 代码：`anger/AngerController.java`\n- Commit：`feat(anger): 实现脱战冷却与距离恢复`")

# ─────────────── TEST ───────────────
add("T-TEST-001", "单元测试：定价引擎", "P0", "4h", "agent",
    "T-PRICE-004", "T-TEST-002, T-TEST-003",
    "以 spike 产出的 `final_pricing_128.json` 为黄金基准，验证定价实现一致。",
    "- 数据：`spikes/design-verify/final_pricing_128.json`",
    """- [ ] 110 条目逐条比对价格，允许 ±0 误差（整数）
- [ ] 关键锚点：僵尸铁锭 **117**、凋灵骷髅头颅 **94**、铜锭 **62**、末影珍珠 **30**、腐肉 **16**、女巫红石 **1**
- [ ] 单调性断言：110/110
- [ ] 边界：0 撞上限、11 撞下限
- [ ] 改 `price_max` 后曲线仍单调""",
    "黄金基准由 Python spike 产出，Java 实现必须复现同样数值。\n若不一致，先确认是 Java 实现错误还是 spike 算法有误，**不要直接改基准**。",
    "- 测试：`PricingGoldenTest.java`\n- Commit：`test(pricing): 添加定价黄金基准测试`")

add("T-TEST-002", "单元测试：门控逻辑真值表", "P0", "3h", "agent",
    "T-SCOPE-002", "T-TEST-001, T-TEST-003",
    "覆盖「已适配 × 白名单」四种组合，以及交易门控的额外条件。",
    "- 设计：`02-design.md` §3.1",
    """- [ ] 4 种基础组合全覆盖
- [ ] 凋灵：已适配 + 不在默认白名单 → **中立化**
- [ ] 末影龙：未适配 → 无论白名单如何都保持原版
- [ ] 第三方 Mod 生物 → 一律 false
- [ ] `trading_enabled=false` → 中立但不可交易
- [ ] `boss_trading_enabled=false` + 凋灵 → 中立但不开界面
- [ ] 白名单动态变更后判定立即改变""",
    "纯逻辑测试，不需要 MC 运行时，用 mock 的 EntityType 即可。",
    "- 测试：`NeutralizationScopeTest.java`\n- Commit：`test(scope): 添加门控真值表测试`")

add("T-TEST-003", "单元测试：补货周期边界", "P0", "3h", "agent",
    "T-TRADE-004", "T-TEST-001, T-TEST-002",
    "验证补货在跨日、小数间隔、长时间离线等边界下的正确性。",
    "- 设计：`02-design.md` §5.3",
    """- [ ] 游戏时间 23999 → 24000 触发补货
- [ ] `restock_interval_days=0.5` → 12000 tick 补一次
- [ ] 离线 100 天后加载 → 只补一次（非补 100 次）
- [ ] `lastRestockDay` 未来时间（存档回滚）→ 容错不崩
- [ ] 补货后 `maxUses` 恢复为 1
- [ ] **不调用** `Villager.restock()`（用 spy 断言）""",
    "用假的 `gameTime` 注入，不依赖真实服务端。",
    "- 测试：`RestockManagerTest.java`\n- Commit：`test(trade): 添加补货边界测试`")

add("T-TEST-004", "P2 验证：原版客户端交易", "P0", "3h", "人工 + agent",
    "T-TRADE-003", "T-TEST-001~003",
    "验证不装模组的原版客户端能否与装了模组的服务端正常交易。",
    "- 遗留：`P1-P4-VERIFY.md` P2（design 阶段未完成）",
    """- [ ] 启动装模组的 NeoForge 服务端
- [ ] 用**原版 1.21.1 客户端**连接（不装任何模组）
- [ ] 右键僵尸能打开交易界面
- [ ] 交易能正常完成，物品正确到手
- [ ] 界面显示的价格与服务端一致
- [ ] Fabric 侧同样验证一遍
- [ ] 结论写入 `P1-P4-VERIFY.md` 并更新宣传文案定位""",
    """理论依据：`openTradingScreen` 是 `Merchant` 的 **default 方法**，
内部走原版 `MerchantMenu` + `ClientboundMerchantOffersPacket`，
全部是原版已有协议，客户端不需要模组代码即可解析。

**但未实测，不得提前写进宣传材料。**

验证方式：
```bash
./gradlew :neoforge:runServer      # 装模组的服务端
# 另开原版启动器 1.21.1，连 localhost:25565
```

⚠️ 若 P2 不成立，需补客户端模组，**影响发布定位文案**，
故本任务提前到 Sprint 3 而非发布阶段。""",
    "- 文档：更新 `P1-P4-VERIFY.md` P2 章节\n- Commit：`docs: 补充 P2 验证结论`",
    "⚠️ 风险任务：结论影响发布文案定位。")

# ─────────────── REL ───────────────
add("T-REL-001", "真机验证清单逐条执行", "P0", "8h", "人工",
    "全部 P0 任务", "T-REL-003",
    "按设计文档的真机验证清单逐条实测，这是发布前的最后质量闸门。",
    "- 设计：`02-design.md` §8.2 真机验证清单\n- 用户偏好：单测全绿不够，必须真机验证",
    """- [ ] 38 个生物逐一验证中立化生效
- [ ] 6 个白名单生物验证保持原版敌对
- [ ] 10 个特殊适配生物单独验证
- [ ] 仇恨三条硬约束逐条验证（玩家攻击/单目标/NPC 不介入）
- [ ] 同族示警 4 格边界与链式截断
- [ ] 交易全流程（打开/成交/每日 1 次/次日补货）
- [ ] 配置热重载可逆性（加白名单→恢复敌对→移除→再中立）
- [ ] 多人场景（A 交易 B 攻击，绿宝石退回）
- [ ] 单人存档 + 专用服务器**双环境**
- [ ] Fabric + NeoForge **双加载器**
- [ ] 逐条勾选，**未测的路径明确列出**""",
    """⚠️ **用户明确要求**：批量修复后先告知已测路径与未测路径，
不要默认所有路径都工作。未测的要明确列出，便于用户自行验证。

建议用 checklist 文件记录，每条标注 ✅/❌/未测。""",
    "- 文档：`RELEASE-CHECKLIST.md`\n- Commit：`docs: 真机验证清单执行记录`",
    "必须人工执行，agent 无法替代。")

add("T-REL-002", "README 中英双语", "P0", "4h", "人工 + agent",
    "T-REL-001", "T-REL-003, T-REL-004",
    "撰写面向**玩家**的 README，开门见山讲这是什么游戏玩法。",
    "- 用户偏好：Release notes 面向玩家/消费者，不是开发日志",
    """- [ ] 首段直接说明：这个模组让敌对生物变成可交易的中立生物
- [ ] 说明核心玩法：不用战斗也能拿到怪物掉落物
- [ ] 说明价格机制（稀有掉落更贵）与每日交易限制
- [ ] 配置项说明（白名单如何用）
- [ ] 支持的加载器与版本
- [ ] 中英双语
- [ ] ❌ **不写**开发过程、bug 修复记录、内部架构""",
    """⚠️ **文档受众纪律**（用户明确要求）：
开发过程细节对公众是噪音。首版说明要讲**这是什么游戏、怎么玩**，
不是修了什么 bug。

好的开头：「厌倦了被苦力怕炸掉你的农场？这个模组让所有敌对生物
变成可以交易的中立生物——用绿宝石换取它们的掉落物，无需战斗。」

坏的开头：「本模组基于 Architectury 实现了 Mixin 注入……」""",
    "- 文档：`README.md`、`README_EN.md`\n- Commit：`docs: 添加中英双语 README`")

add("T-REL-003", "LICENSE 与版权声明核实", "P0", "2h", "人工", "无",
    "T-REL-002, T-REL-004",
    "核实许可证选择的合法性，确认所有素材来源的授权状态。",
    "- 用户偏好：legal 声明必须核实原始仓库授权状态，不能假设",
    """- [ ] 确认代码 LICENSE（设计定为 MIT）
- [ ] **核实**是否使用了任何第三方素材（贴图/音效/代码片段）
- [ ] 若有第三方素材，逐一核实其授权
- [ ] 无授权素材 → 移除或替换，**不得声明 MIT**
- [ ] MC 相关资源的使用符合 Mojang 商业用途准则
- [ ] 若存在权利不明素材，改为「保留所有权利 + 非商用」并注明异议即移除""",
    """⚠️ **法律严谨性**（用户明确要求）：
public 仓库的 LICENSE 不能越权。素材无授权时声明 MIT 是无效的。

本模组目前**纯代码无自制素材**（使用原版贴图与 GUI），
理论上 MIT 无问题，但需确认无复制他人代码片段。""",
    "- 文档：`LICENSE`、README 中的版权段\n- Commit：`docs: 添加 LICENSE 与版权声明`",
    "必须人工核实，不可 agent 代劳。")

add("T-REL-004", "Modrinth / CurseForge 页面文案", "P0", "4h", "人工 + agent",
    "T-REL-002", "T-REL-003",
    "撰写发布平台页面文案，准备截图与标签。",
    "- 用户偏好：面向玩家的文案，不是开发日志",
    """- [ ] 简介一句话说清玩法
- [ ] 详细描述含玩法演示截图（至少 3 张）
- [ ] 截图展示：交易界面、中立的怪物群、配置命令
- [ ] 标签选择（Adventure / Utility / Game Mechanics）
- [ ] 版本兼容性标注（1.21.1 / Fabric / NeoForge）
- [ ] 依赖标注（Architectury API）
- [ ] 中英双语描述""",
    """Modrinth 与 CurseForge 的 markdown 支持略有差异，
CurseForge 对 HTML 更宽容，Modrinth 更严格。建议先写 Modrinth 版本。

⚠️ **P2 结论影响文案**：若客户端需装模组，必须在页面显著位置标注，
否则玩家会遇到连不上服务器的困惑。""",
    "- 文档：`docs/modrinth-page.md`、`docs/curseforge-page.md`\n- Commit：`docs: 添加发布平台页面文案`")

add("T-REL-005", "打 tag 与发布", "P0", "2h", "人工（须用户确认）",
    "T-REL-004, T-REL-003", "无",
    "同步版本号、打 tag、构建 release 产物、上传发布平台。",
    "- 用户偏好：发布前必须等用户确认「发」",
    """- [ ] `gradle.properties` 的 `mod_version` 同步为 `1.0.0`
- [ ] 清理冗余文件，**过程文档不进发布版**
- [ ] `spikes/` 目录不打包进 jar
- [ ] 打 tag `v1.0.0`
- [ ] GitHub Release 创建，附双端 jar
- [ ] 上传 Modrinth
- [ ] 上传 CurseForge
- [ ] 🔒 **每一步发布动作前等用户明确说「发」**""",
    """🔒 **本任务不得自动执行。**

用户偏好（明确记录）：
- 「APK 必须先发包再推下一项」
- 「发布前必须等用户确认『发』—— 即使代码、测试、构建全部就绪，
   也不替用户做发布决策」
- 「发布前先清理冗余文件，不放过程文档进发布版」
- 「打 tag 前 `versionName` 必须同步跟上」

即使前面全部就绪，也必须停下来问用户。""",
    "- 产物：GitHub Release + Modrinth + CurseForge\n- Commit：`chore: 发布 v1.0.0`",
    "🔒 需用户显式确认才能执行。")

for t in T:
    (OUT / f"{t['tid']}.md").write_text(TPL.format(**t), encoding="utf-8")

print(f"已生成 {len(T)} 个任务文件 -> {OUT}")
for t in T:
    print(f"  {t['tid']}.md")
