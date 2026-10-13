# P1~P4 验证报告

- 日期：2026-09-11
- MC 1.21.1 / Java 21 / NeoForge 21.1.250 / Fabric Loader 0.16.9 / Architectury 13.0.11
- 验证方式：**真实构建 + 真实服务端启动 + 字节码静态分析**，无一处推测

---

## 结论速览

| # | 验证项 | 结论 | 证据 |
|---|--------|------|------|
| **P1** | NeoForge 接口注入是否需 AT | ✅ **不需要** | 服务端实测 `Merchant.isAssignableFrom(Mob.class) = true`，accesswidener 为空 |
| **P2** | 客户端不装模组能否交易 | ✅ **能**（2026-10-12 真机） | 零 PAL 类的 mc-client-rpc 客户端连 PAL 服务端，右键开原版 GUI、报价同步，8/8 PASS，见 §P2 |
| **P3** | 注入 Mob 基类 vs 38 个目标类 | ✅ **维持基类方案** | 影响面 82 concrete，额外 44 个，内存开销可忽略 |
| **P4** | `NeutralMob` 冲突 | ✅ **无冲突**（原假设被推翻） | 全 jar 扫描，真实交集为末影人 + 僵尸猪灵 |

---

## P1 —— NeoForge Mixin 接口注入 ✅

### 验证方法

搭建真实 Architectury 三模块工程 `spikes/p1-p3-probe/`，用 `@Mixin(Mob.class) implements Merchant` 注入全部 11 个 abstract 方法，然后**真实启动 NeoForge 专用服务端**。

### 结果

```
================================================================
  Peace And Love —— P1/P3 探针  [NeoForge]
================================================================

【P1】Mixin 注入 Merchant 接口
  Merchant.isAssignableFrom(Mob.class) = true —— 注入成功
```

服务端正常启动完成：`Done (3.119s)! For help, type "help"`

### 关键事实

- **`peaceandlove.accesswidener` 是空文件**（只有注释），全程未添加任何条目
- **NeoForge 侧无需 Access Transformer**
- 双端构建均通过：`BUILD SUCCESSFUL`，产出 `fabric/build/libs/` 与 `neoforge/build/libs/` 两个 jar

### ADR-002 剩余不确定性已清零

方案 A（Mixin 注入 `Merchant`）在 NeoForge 上可行，这是 ADR-002 最后一个待验证点。

---

## P3 —— 注入 Mob 基类的影响面 ✅

### 验证方法

`spikes/design-verify/verify_p3_scope.py` —— 扫描 MC jar 全部 6148 个类，沿 `super` 链递归判定 `Mob` 子类，读 `access_flags` 区分 abstract/concrete。

### 结果

```
Mob 的子类总数        : 103
  其中 abstract        : 21
  其中可实例化(concrete): 82

本模组已适配（v1.0）  : 38
  类名成功匹配上的      : 38 / 38
额外影响面（非目标）  : 44 个可实例化 Mob 子类
```

44 个非目标生物包括：蜜蜂、猫、鸡、牛、海豚、狐狸、铁傀儡、猪、北极熊、羊、雪傀儡、狼、鹦鹉、熊猫、蝾螈、驼、青蛙、山羊、马/驴/骡/羊驼、嗅探兽、悦灵、犰狳等 —— **全部是动物与友好生物**。

### 内存开销

```
Player          pal$tradingPlayer     引用   8 B（压缩指针 4 B）
MerchantOffers  pal$offers            引用   8 B（压缩指针 4 B）
long            pal$lastRestockDay          8 B
──────────────────────────────────────────
合计约 24 B/实例（压缩指针时约 16 B）

1000 只 Mob → 约 24 KB
5000 只 Mob → 约 120 KB
```

`getOffers()` 懒加载，非目标生物的 `pal$offers` 永远为 `null`，实际只多 2 个 null 引用 + 1 个 long。

### 决策：维持方案 A（注入 Mob 基类）

| | 方案 A（Mob 基类） | 方案 B（38 个具体类） |
|---|---|---|
| Mixin 类数 | 1 | 38 target（需按 Goal/Brain 分组） |
| 影响面 | 82 concrete（含 44 非目标） | 精确 38 |
| 内存 | ~24 B × 实例数，可忽略 | 精确 |
| 版本更新维护 | 低 | **高**（每次核对 38 个类名） |
| 第三方 Mod 生物 | 携带字段但被门控拦截 | 永远无能力 |

**理由**：

1. 内存开销可忽略
2. **「携带字段」与「启用行为」是两回事** —— 运行时门控（已适配列表 ∩ 非白名单）已能精确控制行为
3. 方案 B 的 38 个 target 在 MC 版本更新时更易碎

---

## P4 —— `NeutralMob` 冲突检查 ✅（原假设被推翻）

### 原假设

ADR-004 原写：「猪灵 / 猪灵蛮兵 / 疣猪兽 / 僵尸疣猪兽 4 个 Brain 系生物**原本就实现** `NeutralMob`」。

### 实测：这 4 个一个都没实现

`spikes/design-verify/verify_p4_v2.py` 沿继承链递归查找：

| 生物 | 直接接口 | 父类 | 实现 `NeutralMob`？ |
|------|---------|------|-------------------|
| 猪灵 | `CrossbowAttackMob`, `InventoryCarrier` | `AbstractPiglin` | ❌ |
| 猪灵蛮兵 | （无） | `AbstractPiglin` | ❌ |
| 疣猪兽 | `Enemy`, `HoglinBase` | `Animal` | ❌ |
| 僵尸疣猪兽 | `Enemy`, `HoglinBase` | `Monster` | ❌ |
| 监守者 | `VibrationSystem` | `Monster` | ❌ |
| 旋风人 | （无） | `Monster` | ❌ |

### 全量扫描：原版仅 6 个类实现 `NeutralMob`

```
Bee              蜜蜂
IronGolem        铁傀儡
PolarBear        北极熊
Wolf             狼
EnderMan         末影人        ★ 在适配列表
ZombifiedPiglin  僵尸猪灵      ★ 在适配列表
```

### 真实交集：2 个，且都是 Goal 系

| 生物 | 覆写 `NeutralMob` 方法 | 自有 anger 字段 | 引用 universal anger |
|------|----------------------|----------------|---------------------|
| 末影人 | 5 个 | 无 | ✅ 否 |
| 僵尸猪灵 | 5 个 | 无 | ✅ 否 |

**两者均未调用 `forgetCurrentTargetAndRefreshUniversalAnger()`** —— 「仇恨不扩散到其他玩家」不会被原版代码破坏。

### 带出 2 个新的特殊适配

1. **末影人** —— 有 `isLookingAtMe(Player)` / `setBeingStaredAt()` 凝视激怒机制。
   凝视属**主动索敌**，不属于「受玩家攻击」，中立化时须一并禁用。→ `EndermanAdapter`

2. **僵尸猪灵** —— `customServerAiStep()` 内有群体报复（一只被激怒传染周围同类）。
   与本模组「同族示警 4 格单层」**功能重叠**，须禁用原版改由 `KinAlerter` 接管，
   否则双份逻辑导致范围失控。→ `ZombifiedPiglinAdapter`

**特殊适配数：8 → 10。**

### 附带收获

这 2 个生物已实现的 5 个 `NeutralMob` 方法**可直接复用**，无需重复实现存储层。

---

## P2 —— 客户端不装模组能否交易 ✅ 已真机验证（2026-10-12，T-TRADE-003）

### 结论

**成立。** 客户端不含 peace-and-love 任何业务类，连装了 PAL 的 NeoForge 服务端，右键适配生物照常打开原版交易 GUI、报价正常同步，八个门控用例全过（含监守者 boss 门控、仇恨、持物、白名单、未适配牛）。

### 验证方式与边界（措辞严谨）

- 客户端从**独立工程 `mc-client-rpc` 的 `:neoforge:runClient`** 启动（1.21.1 / NeoForge 21.1.250），其 runtime classpath 只有 mc-client-rpc 自身（一个仅开 JSON-RPC 测试端口、**不注册任何游戏内容/网络包/交易逻辑**的自动化驱动 mod）+ architectury，`run/mods` 为空，**零 peaceandlove 类**。
- 服务端是 192.0.2.10 装最新 PAL jar（verify 开关）的 dedicated server。
- 右键经真实 `MultiPlayerGameMode.interact` 发 INTERACT 包；开屏完全由服务端 `openTradingScreen` 的 openMenu + `ClientboundMerchantOffersPacket` 驱动，`MerchantScreen` 由原版类构建。脚本 `tests/automation/verify_trade_interaction.py`，8/8 PASS（日志 `pal_trade_p2.log`）。
- **边界**：这不是「官方启动器零 mod 纯原版客户端」——它带了 mc-client-rpc 这个测试驱动 mod。但该 mod 不参与握手/注册表/交易任何一环，P2 命题（玩家客户端不装 PAL 即可交易）据此成立。协议层 `MerchantMenu` + MerchantOffers 包全原版，与早期理论依据一致。

### 早期理论依据（现已被实测证实）

`Merchant.openTradingScreen(Player, Component, int)` 是 **default 方法**，内部走原版 `MerchantMenu` + `ClientboundMerchantOffersPacket`。这条链路全部是原版已有的网络协议，客户端不需要任何 PAL 代码即可解析。

### 复现方式

```bash
# 服务端：装 PAL 的 NeoForge（192.0.2.10）
# 客户端：从 mc-client-rpc 工程起，而非 peace-and-love
cd D:\Coding\projects\mc-client-rpc && ./gradlew :neoforge:runClient
# 进服后空手右键中立僵尸 → 应直接打开原版交易界面
```

---

## 过程中发现的自身错误（3 处）

诚实记录，避免同类问题重现：

| # | 错误 | 发现方式 | 修正 |
|---|------|---------|------|
| 1 | 称 `Merchant` 有 **9 个方法** | 逐行核对 mappings 原文 | 实为 **12 个**（10 abstract + 2 default）。`extract_api.py` 因常量池反查歧义漏报 `overrideOffers`/`notifyTrade`/`overrideXp`/`openTradingScreen` |
| 2 | 称猪灵等 4 个 Brain 系实现 `NeutralMob` | P4 全量扫描 | 实为末影人 + 僵尸猪灵，且都是 Goal 系 |
| 3 | P4 v2 漏掉末影人 | 人工复核输出 | `EnderMan` 驼峰转 `ender_man`，与 id `enderman` 不匹配，加特例表修正 |

**教训**：混淆表反查**必须带参数描述符**，仅按方法名匹配会被同名方法覆盖。

---

## 环境坑（已记入 memory）

1. **Gradle 9.7.0 与 Architectury Loom 1.7 不兼容** —— Loom 调用已被移除的 `Problems.forNamespace`。须用 Gradle 8.10.2 wrapper。
2. **Loom 子模块必须各自带 `gradle.properties` 写 `loom.platform=fabric|neoforge`** —— 否则 `neoForge()` 依赖方法不存在。
3. **Mixin 包内的类不能被普通代码引用** —— 抛 `IllegalClassLoadError: ... is in a defined mixin package ... and cannot be referenced directly`。工具类须放 mixin 包外。

---

## 对 design 文档的影响

| 文档 | 改动 |
|------|------|
| `adr/002` | `Merchant` 方法数 9 → 12；补 `openTradingScreen` 为 default（GUI 白得）；P1 标记为已验证 |
| `adr/004` | 撤销 P4 原假设；补完整验证结果；特殊适配 8 → 10 |
| `02-design.md` | Mixin 示例补齐 10 个 abstract 方法；`openTradingScreen` 替换手写网络包；新增 `EndermanAdapter` / `ZombifiedPiglinAdapter` |

---

## 遗留

- **P2 已真机闭环**（2026-10-12）——零 PAL 类客户端连 PAL 服务端交易 8/8 通过，见 §P2
- 探针工程 `spikes/p1-p3-probe/` 可直接演进为正式工程骨架（Gradle 配置已验证可用）
