# AGENTS.md

AI 代理（Hermes / Claude Code 等）在本仓库工作时读这个文件。只放**本项目特有的事实**；
通用 MC mod 方法论在 `minecraft-mod-development` skill 里，不在这里重复。

## 项目是什么

Peace And Love —— Minecraft 1.21.1 mod：把敌对生物改造为可中立、可交易、被打会有限度反击。

- 路径：`D:/Coding/projects/peace-and-love`
- 双端：Architectury（common / fabric / neoforge），modid `peaceandlove`，包名 `top.windyvalley.peaceandlove`
- MC 1.21.1 + Java 21，NeoForge 21.1.250，Fabric Loader 0.16.9
- Gradle 8.10.2（**不要升 9.x**，与 Architectury Loom 1.7.x 不兼容）
- 版本号等所有构建参数以 `gradle.properties` 为唯一来源

## 常用命令

```bash
./gradlew build                  # 双端构建
./gradlew :neoforge:genSources   # 读 MC 方法体前先跑（neoforge sources jar 不含 net/minecraft）
./gradlew test                   # 全量单测
./gradlew :neoforge:runClient    # 真机客户端验证
```

## 架构要点（本项目特有的定论）

代码在 `common/src/main/java/top/windyvalley/peaceandlove/`：`anger/`（愤怒与示警）、
`neutralize/`（中立化策略）、`trade/`（交易）、`pricing/`（掉落定价）、`scope/`（生物分类）、
`config/`、`mixin/`、`verify/`。

- **愤怒入口只认玩家攻击**：`DamageSource.getEntity() instanceof Player`。NPC 互殴/环境伤害走原版逻辑，mod 不介入。
- **同族示警与生物自身反击是两条解耦的链**，不要把反击入口收窄成「仅玩家攻击」。
- 所有 7 种 C 类生物（Giant/Guardian/ElderGuardian/Ghast/Slime/MagmaCube/Phantom）的同族示警统一走
  `LivingEntityHurtMixin → KinAlerter` 直调，**不依赖运行时 addGoal**（原版 HurtByTargetGoal.alertOthers
  仅对构造期注册的 goal 可靠，运行时 addGoal 触发不可靠）。
- A/B/C 生物分类、HurtByTargetGoalMixin 三门控、NeutralMob 分流等设计判据见
  `minecraft-mod-development` skill 及 `docs/02-design.md`。
- 循环标记判定用 `execute on target` + marker 布尔通道（比行为位移或读 NBT 可靠）。
- Mixin 包里只能放 @Mixin 类；辅助类放普通包，否则 IllegalClassLoadError。
- Loom 子模块必须在各自 `gradle.properties` 写 `loom.platform=neoforge|fabric`。

## 文档与流程

- 设计与验证文档在 `docs/`（需求、设计、ADR、P1-P4 验证记录）。
- commit message 用中文，写清根因/修法/副作用；偏好分批提交。
- 用户会真机验证，单测全绿不够：行为改动也要说明已测/未测路径。
- **发布决策权在用户**：构建、测试全就绪也不替用户发版，等明确确认。
