"""
生成 T-SETUP-003 的分层包结构 + package-info.java
=================================================
依赖方向（不得反向）：
    mixin → (trade, neutralize, anger) → scope → config
    pricing → (独立，仅依赖 config)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BASE = ROOT / "common/src/main/java/top/windyvalley/peaceandlove"

PKGS = {
    "config": {
        "title": "配置系统",
        "desc": """加载与热重载模组配置，是整个依赖链的最底层。

<p>本包**不依赖任何其他业务包**。配置项包括：白名单、交易开关、
仇恨参数（脱战时长、示警半径）、定价上限等。

<p>白名单支持运行时热重载 —— 修改后无需重启服务端，
通过 {@code /peaceandlove reload} 立即生效。""",
        "deps": "无（最底层）",
    },
    "scope": {
        "title": "生效范围判定",
        "desc": """决定一个生物是否应当被中立化，是全模组的**判定枢纽**。

<p>核心规则（双重门控）：
<pre>
被中立化 = 在已适配列表中 AND 不在白名单中
</pre>

<p>「已适配列表」是代码能力边界（v1.0 共 38 种，编译期常量），
「白名单」是运行时配置。两者语义不同，不可混为一谈：
第三方 Mod 的生物天然不在已适配列表内，因此完全不受影响 ——
这不是靠白名单实现的。

<p><b>本包不得依赖 trade / neutralize / anger</b>，否则形成循环依赖。""",
        "deps": "config",
    },
    "pricing": {
        "title": "定价系统",
        "desc": """把掉落物的「每击杀期望产出」(epk) 映射为绿宝石价格。

<p>采用对数曲线：
<pre>
pos   = log(2 / epk) / log(400)
price = clamp(1 + 127 × pos, 1, 128)
</pre>

<p>上限 128 源于 {@code MerchantOffer} 的双输入槽设计限制。
110 个掉落物条目经实测全部单调、无一撞顶。

<p>本包**独立于中立化与交易逻辑**，仅依赖 config 读取定价参数，
因此可独立测试与并行开发。""",
        "deps": "config",
    },
    "trade": {
        "title": "交易系统",
        "desc": """为被中立化的生物提供原版 Merchant 交易能力。

<p>实现方式：通过 Mixin 向 {@code Mob} 基类注入原版 {@code Merchant}
接口（详见 ADR-002），复用整套原版交易 GUI 与网络协议，
不自建 Menu、不写自定义数据包。

<p>补货策略：{@code MerchantOffer.maxUses = 1} + 自实现的每游戏日
{@code resetAllUses()}。**不使用** {@code Villager.restock()} ——
那会连带引入 gossip / demand 等副作用（详见 ADR-003）。""",
        "deps": "scope, pricing, config",
    },
    "neutralize": {
        "title": "生物中立化",
        "desc": """移除敌对生物的主动索敌行为，使其默认不攻击玩家。

<p>双策略（详见 ADR-004）：
<ul>
  <li><b>Goal 系</b>（32 种）—— 通过 {@code GoalSelector.removeAllGoals(Predicate)}
      移除 {@code NearestAttackableTargetGoal} 等主动索敌 Goal</li>
  <li><b>Brain 系</b>（6 种）—— 拦截 Brain 的 activity 更新</li>
</ul>

<p>特殊适配 10 种，其中末影人的凝视激怒、僵尸猪灵的群体报复
需单独处理（P4 验证发现，详见 docs/P1-P4-VERIFY.md）。

<p>白名单热重载时通过 WrappedGoal 快照恢复原始 Goal。""",
        "deps": "scope, config",
    },
    "anger": {
        "title": "仇恨管理",
        "desc": """管理被中立化生物受攻击后的反击行为。

<p>三条硬约束：
<ol>
  <li><b>仅玩家攻击触发</b> —— 铁傀儡、村民卫兵、怪物内斗、
      环境伤害一律不介入。玩家的投射物、TNT、owner 为玩家的宠物视同玩家攻击</li>
  <li><b>仇恨锁定攻击者本人</b> —— 按 UUID 单目标锁定，
      玩家 A 动手不会牵连旁边的玩家 B</li>
  <li><b>同族示警不链式扩散</b> —— 4 格球形内同 EntityType 的生物被通知，
      但被通知者不再向外传播</li>
</ol>

<p>脱战条件：30 秒无交互 或 距离超过 32 格，恢复中立。""",
        "deps": "scope, config",
    },
    "mixin": {
        "title": "Mixin 注入",
        "desc": """所有 Mixin 类的唯一存放位置，是依赖链的最上层。

<p><b>纪律：本包内的类不得被普通代码直接引用</b> ——
Mixin 类由 Mixin 框架在类加载期处理，普通代码引用会抛
{@code IllegalClassLoadError: ... cannot be referenced directly}。

<p>工具类、结果收集器等辅助代码必须放在本包**之外**。
这个坑在 P1 验证阶段实际踩过一次。

<p>每新增一个 Mixin，必须同步在
{@code peaceandlove-common.mixins.json} 的 mixins 数组中登记。""",
        "deps": "trade, neutralize, anger（最上层）",
    },
}

TPL = """/**
 * {title}。
 *
 * <p>{desc}
 *
 * <p><b>依赖：</b>{deps}
 *
 * @see top.windyvalley.peaceandlove.PeaceAndLove
 */
package top.windyvalley.peaceandlove.{pkg};
"""

created = []
for pkg, info in PKGS.items():
    d = BASE / pkg
    d.mkdir(parents=True, exist_ok=True)
    f = d / "package-info.java"
    f.write_text(
        TPL.format(pkg=pkg, title=info["title"], desc=info["desc"], deps=info["deps"]),
        encoding="utf-8",
        newline="\n",
    )
    created.append(f"{pkg}/package-info.java")

print("已创建包结构：")
for c in created:
    print(f"  {c}")
print(f"\n共 {len(created)} 个包")
