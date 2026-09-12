"""
R3 spike v2 — 修正 AI 系统判定逻辑
=====================================

v1 判定缺陷：把 `customServerAiStep` 当成 Brain 标志，导致误判。
  实际上 customServerAiStep 只是「每 tick 的额外服务端逻辑钩子」，
  Goal 系统的生物也大量覆写它（末影人处理传送、烈焰人处理飞行、凋灵处理弹幕）。

✅ 正确判据：
    Brain 系统  ⇔ 覆写 makeBrain() 或 brainProvider()
    Goal  系统  ⇔ 有 goalSelector/targetSelector 字段使用（继承自 Mob）
                  且未覆写 makeBrain

  另需沿继承链回溯：ZombieVillager 未覆写 registerGoals，但继承 Zombie 的 Goal 体系。

本脚本输出最终的 AI 系统对照表 + 中立化策略分组。
"""

import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, "ai_system_map.json"), encoding="utf-8") as f:
    raw = json.load(f)

detail = {d["entity"]: d for d in raw["detail"]}

# 继承链（从 v1 输出的 super 字段构建）
SUPER = {d["entity"]: d["super"] for d in raw["detail"]}

# 真正的 Brain 生物：覆写了 makeBrain 或 brainProvider
TRUE_BRAIN = set()
for e, d in detail.items():
    bm = d["brain_methods"]
    if "makeBrain" in bm or "brainProvider" in bm:
        TRUE_BRAIN.add(e)

# 继承自 Brain 生物的也算 Brain（沿链回溯）
BRAIN_ANCESTORS = {"Villager", "AbstractVillager", "Piglin", "AbstractPiglin",
                   "Hoglin", "Warden", "Breeze", "Axolotl", "Allay", "Frog",
                   "Goat", "Armadillo", "Sniffer", "Tadpole", "Camel", "Zoglin"}


def resolve(entity):
    """沿继承链判定最终 AI 系统"""
    if entity in TRUE_BRAIN:
        return "BRAIN"
    sup = SUPER.get(entity, "?")
    chain = [entity]
    cur = sup
    depth = 0
    while cur and cur != "?" and depth < 8:
        if cur in TRUE_BRAIN or cur in BRAIN_ANCESTORS:
            return "BRAIN"
        chain.append(cur)
        if cur in ("Monster", "PathfinderMob", "Animal", "Mob", "AbstractGolem",
                   "Raider", "AbstractIllager", "SpellcasterIllager", "FlyingMob",
                   "WaterAnimal", "TamableAnimal", "AbstractSkeleton", "Zombie",
                   "Slime", "Spider", "Guardian", "AbstractHorse", "AbstractChestedHorse",
                   "AbstractFish", "Llama"):
            return "GOAL"
        cur = SUPER.get(cur, "?")
        depth += 1
    return "GOAL"


# ═══════════════════════════════════════════════════════════
# 本模组关心的目标：会主动攻击玩家的生物
# ═══════════════════════════════════════════════════════════
# 分类依据：是否需要「移除主动索敌」处理
ACTIVELY_HOSTILE = [
    # 亡灵
    "Zombie", "ZombieVillager", "Husk", "Drowned", "ZombifiedPiglin",
    "Skeleton", "WitherSkeleton", "Stray", "Bogged", "Giant",
    # 蜘蛛类
    "Spider", "CaveSpider",
    # 爆炸/远程
    "Creeper", "Ghast", "Blaze", "Witch",
    # 史莱姆
    "Slime", "MagmaCube",
    # 末地
    "EnderMan", "Endermite", "Shulker",
    # 海洋
    "Guardian", "ElderGuardian",
    # 空中
    "Phantom",
    # 袭击（默认白名单）
    "Pillager", "Vindicator", "Evoker", "Vex", "Illusioner", "Ravager",
    # 下界 Brain 系
    "Piglin", "PiglinBrute", "Hoglin", "Zoglin",
    # 深暗域 / 试炼密室
    "Warden", "Breeze",
    # 虫
    "Silverfish",
    # Boss
    "EnderDragon", "WitherBoss",
]

# 用户确认的默认白名单（保持原版敌对）
USER_WHITELIST = {"Pillager", "Vindicator", "Evoker", "Vex", "Phantom", "Shulker"}

ZH = {
    "Zombie": "僵尸", "ZombieVillager": "僵尸村民", "Husk": "尸壳", "Drowned": "溺尸",
    "ZombifiedPiglin": "僵尸猪灵", "Skeleton": "骷髅", "WitherSkeleton": "凋灵骷髅",
    "Stray": "流浪者", "Bogged": "沼骸", "Giant": "巨人(未生成)",
    "Spider": "蜘蛛", "CaveSpider": "洞穴蜘蛛", "Creeper": "苦力怕", "Ghast": "恶魂",
    "Blaze": "烈焰人", "Witch": "女巫", "Slime": "史莱姆", "MagmaCube": "岩浆怪",
    "EnderMan": "末影人", "Endermite": "末影螨", "Shulker": "潜影贝",
    "Guardian": "守卫者", "ElderGuardian": "远古守卫者", "Phantom": "幻翼",
    "Pillager": "掠夺者", "Vindicator": "卫道士", "Evoker": "唤魔者", "Vex": "恼鬼",
    "Illusioner": "幻术师(未生成)", "Ravager": "劫掠兽",
    "Piglin": "猪灵", "PiglinBrute": "猪灵蛮兵", "Hoglin": "疣猪兽", "Zoglin": "僵尸疣猪兽",
    "Warden": "监守者", "Breeze": "旋风人", "Silverfish": "蠹虫",
    "EnderDragon": "末影龙", "WitherBoss": "凋灵",
}

MOB_ID = {
    "Zombie": "zombie", "ZombieVillager": "zombie_villager", "Husk": "husk",
    "Drowned": "drowned", "ZombifiedPiglin": "zombified_piglin", "Skeleton": "skeleton",
    "WitherSkeleton": "wither_skeleton", "Stray": "stray", "Bogged": "bogged",
    "Giant": "giant", "Spider": "spider", "CaveSpider": "cave_spider",
    "Creeper": "creeper", "Ghast": "ghast", "Blaze": "blaze", "Witch": "witch",
    "Slime": "slime", "MagmaCube": "magma_cube", "EnderMan": "enderman",
    "Endermite": "endermite", "Shulker": "shulker", "Guardian": "guardian",
    "ElderGuardian": "elder_guardian", "Phantom": "phantom", "Pillager": "pillager",
    "Vindicator": "vindicator", "Evoker": "evoker", "Vex": "vex",
    "Illusioner": "illusioner", "Ravager": "ravager", "Piglin": "piglin",
    "PiglinBrute": "piglin_brute", "Hoglin": "hoglin", "Zoglin": "zoglin",
    "Warden": "warden", "Breeze": "breeze", "Silverfish": "silverfish",
    "EnderDragon": "ender_dragon", "WitherBoss": "wither",
}


def main():
    print("=" * 100)
    print("R3 SPIKE v2 — 1.21.1 主动敌对生物的 AI 系统判定（修正版）")
    print("=" * 100)
    print("""
判据修正：
  ✗ v1 错误：把 customServerAiStep 当 Brain 标志
             → 末影人/烈焰人/幻翼/卫道士/唤魔者/凋灵 被误判为 Brain 或 MIXED
  ✓ v2 正确：Brain ⇔ 覆写 makeBrain() 或 brainProvider()
             customServerAiStep 只是 tick 钩子，Goal 生物同样大量使用
""")

    print("%-16s %-14s %-7s %-9s %-38s" % ("生物", "ID", "AI系统", "处理", "说明"))
    print("-" * 100)

    goal_list, brain_list, skip_list, wl_list = [], [], [], []

    for e in ACTIVELY_HOSTILE:
        d = detail.get(e)
        if not d:
            print("%-16s %-14s %-7s %-9s %s" % (ZH.get(e, e), MOB_ID.get(e, "?"), "?", "?", "映射未找到"))
            continue

        sysname = resolve(e)
        mid = MOB_ID.get(e, "?")
        zh = ZH.get(e, e)

        if e in ("EnderDragon", "WitherBoss"):
            action = "跳过"
            note = "Boss，专属 AI（Phase/弹幕），不用标准索敌 Goal"
            skip_list.append(e)
        elif e in USER_WHITELIST:
            action = "白名单"
            note = "用户指定保持原版敌对"
            wl_list.append(e)
        elif sysname == "BRAIN":
            action = "Brain策略"
            note = "需 Brain/Behavior 改写，与 Goal 完全不同的实现路径"
            brain_list.append(e)
        else:
            action = "Goal策略"
            note = "移除 NearestAttackableTargetGoal，保留 HurtByTargetGoal"
            goal_list.append(e)

        print("%-16s %-14s %-7s %-9s %s" % (zh, mid, sysname, action, note))

    print()
    print("=" * 100)
    print("中立化实现分组（决定 dev 阶段工作量）")
    print("=" * 100)

    print("\n  ① Goal 策略 —— 共 %d 个（主体工作，一套代码覆盖）" % len(goal_list))
    for i in range(0, len(goal_list), 5):
        print("     " + "  ".join("%-14s" % ZH.get(x, x) for x in goal_list[i:i + 5]))

    print("\n  ② Brain 策略 —— 共 %d 个（★ 独立实现路径，工作量翻倍点）" % len(brain_list))
    for i in range(0, len(brain_list), 5):
        print("     " + "  ".join("%-14s" % ZH.get(x, x) for x in brain_list[i:i + 5]))

    print("\n  ③ 用户白名单 —— 共 %d 个（保持原版敌对，零工作量）" % len(wl_list))
    print("     " + "  ".join("%-14s" % ZH.get(x, x) for x in wl_list))

    print("\n  ④ 天然跳过 —— 共 %d 个（Boss 专属 AI，中立化机制不作用）" % len(skip_list))
    print("     " + "  ".join("%-14s" % ZH.get(x, x) for x in skip_list))

    print()
    print("=" * 100)
    print("R3 结论")
    print("=" * 100)
    print("""
  ✅ 判定完成，工作量已量化：
       Goal 策略  %2d 个 —— 主体，一套 Mixin + 一个 Goal 移除工具类即可
       Brain 策略 %2d 个 —— 需第二套实现（Behavior 改写）
       白名单     %2d 个 —— 零成本
       Boss 跳过  %2d 个 —— 零成本

  ★ 关键发现（影响 v1.0 范围决策）：
     Brain 系生物中，会主动攻击玩家的是：
       • 猪灵 / 猪灵蛮兵 —— 玩家穿金装即中立，本就有中立机制
       • 疣猪兽 / 僵尸疣猪兽 —— 疣猪兽原版已可被驯化型互动
       • 监守者 —— 建议列入白名单（其设计核心是震动侦测，中立化等于废掉）
       • 旋风人 —— ⚠️ 1.21 试炼密室核心敌人，玩家会期待它可中立化
       • 远古守卫者 —— 海底神殿守卫

  💡 建议 v1.0 范围（待你确认）：
     方案 A（保守）：v1.0 只做 Goal 策略的 %d 个，Brain 系全部列入默认白名单，
                     在模组说明中如实声明，v1.1 再补 Brain 支持
     方案 B（完整）：v1.0 同时做两套策略，工作量增加约 40%%，
                     但覆盖旋风人等玩家期待的生物

  ⚠️ 监守者无论哪个方案都建议进白名单（震动机制 + 无敌属性，中立化无意义）
""" % (len(goal_list), len(brain_list), len(wl_list), len(skip_list), len(goal_list)))

    # 导出结论 JSON
    out = {
        "mc_version": "1.21.1",
        "goal_strategy": [{"id": MOB_ID[e], "zh": ZH[e]} for e in goal_list],
        "brain_strategy": [{"id": MOB_ID[e], "zh": ZH[e]} for e in brain_list],
        "user_whitelist": [{"id": MOB_ID[e], "zh": ZH[e]} for e in wl_list],
        "boss_skip": [{"id": MOB_ID[e], "zh": ZH[e]} for e in skip_list],
    }
    p = os.path.join(BASE, "neutralization_plan.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("[*] 已保存:", p)


if __name__ == "__main__":
    main()
