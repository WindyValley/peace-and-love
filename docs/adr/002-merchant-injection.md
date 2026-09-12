# ADR-002: 通过 Mixin 注入 `Merchant` 接口实现怪物交易

## 状态

Accepted（2026-09-11）
—— **本 ADR 推翻了 requirements 阶段的初始倾向（自建 Menu），依据是 spike 实测**

## 背景

需求要求玩家能像与村民交易一样，右键中立怪物打开交易界面（`../01-requirements.md` FR-2.1）。

原版中只有 `AbstractVillager`（村民、流浪商人）实现了 `Merchant` 接口，普通 `Mob` 没有交易能力。

**requirements 阶段的初始判断**（未经验证）：
> `Merchant` 接口可能依赖村民专属的字段与状态（声望、职业、工作站点），给普通 Mob 注入成本高，倾向自建 Menu + 自定义网络包。

这个判断在 spike 中被**字节码实测推翻**。

## 决策

采用 **Mixin 注入 `Merchant` 接口**，复用原版 `MerchantMenu` 与网络层。

### 实测依据（1.21.1 官方 server.jar + mappings）

`net.minecraft.world.item.trading.Merchant` 的完整方法列表：

```java
// 10 个 abstract —— 均无字段依赖
void            setTradingPlayer(Player)
Player          getTradingPlayer()
MerchantOffers  getOffers()
void            overrideOffers(MerchantOffers)
void            notifyTrade(MerchantOffer)
void            notifyTradeUpdated(ItemStack)
int             getVillagerXp()
void            overrideXp(int)
boolean         showProgressBar()
SoundEvent      getNotifyTradeSound()
boolean         isClientSide()

// 2 个 default —— 无需覆写
boolean canRestock()
void    openTradingScreen(Player, Component, int)   // ★ GUI 白得
```

> ⚠️ **修正记录**：早先 `extract_api.py` 因常量池反查歧义**漏报了 4 个方法**
> （`overrideOffers` / `notifyTrade` / `overrideXp` / `openTradingScreen`），一度记为"9 个方法"。
> 以 mappings 原文逐行核对为准：**共 12 个（10 abstract + 2 default）**。

**关键事实：**

1. 全部 **12 个方法，零字段依赖** —— 是纯行为接口，不需要村民的声望/职业/工作站点
2. `showProgressBar()` 直接 `return false` 即可（不显示村民等级进度条）
3. `canRestock()` 与 **`openTradingScreen()` 均有 default 实现**，无需覆写 —— 后者意味着**打开 GUI 的完整流程都是白得的**
4. `MerchantOffer` 已内置 `uses` / `maxUses` / `resetUses()` / `isOutOfStock()` —— 交易次数与补货语义**完全不用自己写**（详见 ADR-003）
5. `AbstractVillager` 直接实现 `Merchant`，有现成的照抄对象
6. `ServerPlayer.openMenu(MenuProvider)` 与 `Player.sendMerchantOffers(...)` 均为原版已有，网络同步免费

### 注入范围

注入 `net.minecraft.world.entity.Mob` 基类，运行时通过 `NeutralizationScope` 判定是否启用（详见 ADR-004）。

> ✅ **P3 已验证**：`Mob` 有 82 个可实例化子类，注入基类额外波及 44 个非目标生物（均为动物/友好生物）。
> 每实例开销约 24 B 且 `offers` 懒加载，实测判定为可忽略。**维持注入基类方案**，详见 `../P1-P4-VERIFY.md`。

## 后果

### 正面

- **工作量显著低于自建方案** —— 无需写 Screen、贴图、网络包、槽位同步
- GUI 外观、交互逻辑、售罄显示全部与原版村民一致，玩家零学习成本
- 交易次数与补货直接落在 `MerchantOffer` 上，与原版语义一致
- **客户端很可能不需要安装模组**（P2 待验证）—— 若成立是重要卖点，服务器单边安装即可

### 负面

- Mixin 注入接口，与其他修改 `Mob` 的 Mod 存在潜在冲突（见 `../RISKS.md` R10）
- 注入基类意味着所有 `Mob` 子类都携带 `Merchant` 相关字段 —— ✅ P3 实测为 82 个可实例化子类（额外 44 个非目标），每实例约 24 B 且懒加载，可忽略
- ~~NeoForge 侧可能需要配置 Access Transformer（P1 待验证）~~ → ✅ **P1 已验证：不需要 AT**，NeoForge 21.1.250 上 `Merchant.isAssignableFrom(Mob.class) = true`，accesswidener 为空
- 受限于 `MerchantOffer` 的双输入槽设计，单笔交易价格上限为 128（64+64），无法更高

### 中性

- 交易界面会显示村民风格的 UI，对"跟僵尸做买卖"的场景来说观感略微违和，但也可视为特色

## 备选方案

### 选项 B：自建 Menu + 自定义网络包

- 优点：完全自主可控；UI 可定制成怪物主题；不受 `MerchantOffer` 双槽限制
- 缺点：需实现 20+ 个方法；自写 Screen 与贴图；自定义 packet ×3；客户端**必须**安装模组；交易次数/补货逻辑全部自写
- 不选的原因：实测发现方案 A 的成本远低于预期，选项 B 的额外自由度不值得数倍的工作量

### 选项 C：交互时在怪物位置生成隐形村民代理

- 优点：完全不碰 `Mob` 类，Mixin 冲突面最小
- 缺点：需同步代理实体与本体的位置、存活、移除；玩家可能用其他手段与代理交互产生怪异行为；实体计数增加；跨维度/区块卸载边界情况多
- 不选的原因：看似取巧，实际边界情况远多于直接注入

## 待验证（design 阶段最小原型）

| # | 验证项 | 影响 |
|---|--------|------|
| **P1** | NeoForge 的 Mixin 接口注入是否需要 Access Transformer | 若需要则要额外维护 `accesstransformer.cfg` |
| **P2** | 客户端不装模组能否正常交易 | 若能则是重要卖点，需在文档中明确声明 |
| **P3** | 注入 `Mob` 基类 vs 38 个已适配目标类 | 前者代码少但影响面大，后者反之 |

## 回退路径

若 P1 显示 NeoForge 接口注入受阻严重，改为对 38 个已适配目标类逐一注入 —— 代码量增加但机制不变，不影响架构。

若 P2 显示客户端必须安装，则在发布页明确标注，不影响功能可用性。

## 参考资料

- 实测脚本：`spikes/design-verify/extract_api.py`、`spikes/r2-trade/analyze.py`
- spike 报告：`../SPIKE-REPORT.md` R2 章节
