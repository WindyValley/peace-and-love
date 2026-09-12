"""
R1 spike — 战利品表定价算法可行性验证
==========================================
基于从 1.21.1 client.jar 提取的 100 张实体战利品表 JSON，
模拟评估：无需 Mixin 能读到什么，哪些地方必须用 Mixin Accessor。

输出：定价算法可行性结论 + 定价示例（僵尸/凋灵骷髅/苦力怕）
"""

import json
import os
import math
import sys

BASE = os.path.join(os.path.dirname(__file__), "loot_tables")

# 标价参数（spike 阶段用固定值，后续可配置）
PRICE_MIN = 1
PRICE_MAX = 64
PRICE_MULTIPLIER = 16.0  # 将期望产出 → 绿宝石的缩放因子


def uniform_min_max(count_dict):
    """解析 uniform count 的 min/max，返回 (min, max)"""
    if count_dict.get("type") == "minecraft:uniform":
        return float(count_dict.get("min", 0)), float(count_dict.get("max", 1))
    return 0.0, 1.0


def expected_count(functions):
    """
    估算一条 entry 在 looting=0 下的期望产出数量。
    只解析 set_count 和 enchanted_count_increase（取 looting 0 时的值）。
    """
    c_min, c_max = 1.0, 1.0  # 默认 1 个
    for fn in (functions or []):
        ftype = fn.get("function")
        if ftype == "minecraft:set_count":
            # set_count 通常有 add=false，count 是 uniform 或 fixed
            cnt = fn.get("count", {})
            if cnt.get("type") == "minecraft:uniform":
                c_min, c_max = float(cnt["min"]), float(cnt["max"])
            else:
                c_min = c_max = float(cnt)
        elif ftype == "minecraft:enchanted_count_increase":
            # looting 0 → 不加成, count 为 uniform(0, max) 层
            cnt = fn.get("count", {})
            if cnt.get("type") == "minecraft:uniform":
                bonus_min, bonus_max = float(cnt["min"]), float(cnt["max"])
                # looting 0 → 加成 0
                c_min += 0.0
                c_max += 0.0
    # 期望值 = (min + max) / 2
    return (c_min + c_max) / 2.0


def is_killed_by_player(conditions):
    """检查条件数组中是否包含 killed_by_player（判定为真。不包括则判为假）"""
    if not conditions:
        return False
    for c in conditions:
        if c.get("condition") == "minecraft:killed_by_player":
            return True
    return False


def get_base_probability(conditions):
    """
    从条件中提取无 looting 时的基础概率。
    处理:
      - killed_by_player: 假定为真 (1.0, 由 is_killed_by_player 过滤)
      - random_chance_with_enchanted_bonus: 取 unenchanted_chance
      - random_chance: 取 chance
      - entity_properties / other: 无法静态求值 → 保守估计 0.3
    注意: 本 spike 只读 JSON, 不涉及 Mixin。运行时这些字段可能是 private 的。
    """
    if not conditions:
        return 1.0  # 无条件 = 必定触发

    prob = 1.0
    for c in conditions:
        cond_type = c.get("condition")
        if cond_type == "minecraft:killed_by_player":
            prob *= 1.0  # 我们假定以玩家击杀为基准
        elif cond_type == "minecraft:random_chance_with_enchanted_bonus":
            # unenchanted_chance 是 public JSON field, 但在运行时类中是 private float
            # ★ 这是 Mixin Accessor 的必入点
            prob *= float(c.get("unenchanted_chance", 0.025))
        elif cond_type == "minecraft:random_chance":
            prob *= float(c.get("chance", 1.0))
        elif cond_type in ("minecraft:any_of", "minecraft:all_of"):
            # 递归处理嵌套条件
            inner = c.get("terms", [])
            if cond_type == "minecraft:any_of":
                # 至少一个满足 = 很难静态计算，保守取最大值
                inner_probs = []
                for t in inner:
                    ip = get_base_probability([t])
                    inner_probs.append(ip)
                prob *= max(inner_probs) if inner_probs else 1.0
            else:  # all_of
                for t in inner:
                    prob *= get_base_probability([t])
        else:
            # entity_properties, alternative, weather_check, etc.
            # 保守估计 0.3 (既不完全忽略也不完全信任)
            prob *= 0.3
    return prob


def canonical_item_name(item_id):
    """简化物品 ID (minecraft:stone → stone)"""
    return item_id.split(":", 1)[-1] if ":" in item_id else item_id


def analyze_loot_table(path):
    """分析一张实体战利品表，返回 [(item_id, roll_count, prob, expected_per_kill), ...]"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    seq_id = data.get("random_sequence", "unknown")
    pools = data.get("pools", [])
    results = []

    for pi, pool in enumerate(pools):
        rolls = float(pool.get("rolls", 1.0))
        # bonus_rolls 暂时忽略（looting 相关）
        entries = pool.get("entries", [])
        pool_conditions = pool.get("conditions", None)

        # pool-level conditions (如 zombie 无, 但可以有)
        pool_prob = get_base_probability(pool_conditions) if pool_conditions else 1.0

        # entries 在 pool 内的权重概率
        total_weight = 0.0
        for e in entries:
            w = float(e.get("weight", 1))
            total_weight += w

        for ei, e in enumerate(entries):
            etype = e.get("type")
            if etype == "minecraft:item":
                item = e.get("name", "unknown")
            elif etype == "minecraft:tag":
                # tag 扩展条目，无法直接得到 concrete item 列表
                item = f"@tag:{e.get('name','?')}"
            elif etype == "minecraft:alternatives":
                # alternatives: 按条件顺序，命中第一个就退出
                item = "@alternatives"
            elif etype == "minecraft:empty":
                item = "@empty"
            elif etype == "minecraft:loot_table":
                item = f"@ref:{e.get('name','?')}"
            else:
                item = f"@{etype}"

            weight = float(e.get("weight", 1))
            weight_prob = weight / total_weight if total_weight > 0 else 1.0

            # 独立条件
            entry_conditions = e.get("conditions", None)
            entry_prob = get_base_probability(entry_conditions) if entry_conditions else 1.0

            # 数量
            functions = e.get("functions", None)
            cnt = expected_count(functions)

            # 考虑 kill_by_player 条件在 pool/entry 级别
            kbp = is_killed_by_player(pool_conditions) or is_killed_by_player(entry_conditions)

            # 最终概率: pool_condition * entry_weight * entry_condition
            effective_prob = pool_prob * weight_prob * entry_prob

            # 每次击杀期望产出 = rolls * probability * expected_count
            expected_per_kill = rolls * effective_prob * cnt

            results.append({
                "item": item,
                "type": etype,
                "rolls": rolls,
                "weight": weight,
                "weight_prob": round(weight_prob, 4),
                "pool_cond_prob": round(pool_prob, 4),
                "entry_cond_prob": round(entry_prob, 4),
                "effective_prob": round(effective_prob, 6),
                "expected_count": round(cnt, 2),
                "expected_per_kill": round(expected_per_kill, 4),
                "killed_by_player": kbp,
            })

    return seq_id, results


def compute_price(expected_per_kill):
    """
    核心定价函数：期望产出 → 绿宝石价格。
    原则：越罕见越贵。
    """
    if expected_per_kill <= 0.0001:
        return PRICE_MAX
    raw = PRICE_MULTIPLIER / expected_per_kill
    clipped = max(PRICE_MIN, min(PRICE_MAX, raw))
    return int(clipped)


def main():
    print("=" * 72)
    print("R1 SPIKE — 战利品表定价算法验证 (1.21.1 原版 JSON)")
    print("=" * 72)

    targets = ["zombie.json", "wither_skeleton.json", "creeper.json",
               "skeleton.json", "drowned.json", "blaze.json"]

    for fname in targets:
        path = os.path.join(BASE, fname)
        if not os.path.exists(path):
            print(f"\n[!] {fname} 未找到，跳过")
            continue

        seq_id, items = analyze_loot_table(path)
        mob_name = fname.replace(".json", "")
        print(f"\n{'─' * 72}")
        print(f"  ★ {mob_name}")
        print(f"  sequence: {seq_id}")
        print(f"{'─' * 72}")

        if not items:
            print("  (无可用条目)")
            continue

        print(f"  {'物品':<30} {'类型':<20} {'概率':>8} {'期望/击杀':>10} {'价格':>4}")
        print(f"  {'-'*30} {'-'*20} {'-'*8} {'-'*10} {'-'*4}")

        for r in items:
            item_display = r["item"].split(":")[-1] if ":" in r["item"] else r["item"]
            et = r["type"].split(":")[-1] if ":" in r["type"] else r["type"]
            price = compute_price(r["expected_per_kill"])
            kbp_mark = " [kbp]" if r["killed_by_player"] else ""
            print(f"  {item_display:<30} {et:<20} {r['effective_prob']:>8.4f} "
                  f"{r['expected_per_kill']:>10.3f} {price:>3}{kbp_mark}")

    print()
    print("=" * 72)
    print("R1 关键技术发现")

    print("""
  ✅ 结构可访问性 — LootTable 1.21.1 中为 record，pools() 为 public accessor
                    LootPool.entries() 亦为 public → 无需 Mixin 即可遍历结构

  ⚠️ 条件参数需 Mixin — 以下类的字段为 private，需 Mixin Accessor:
       • LootItemRandomChanceCondition.probability (float)
       • LootItemRandomChanceWithEnchantedBonusCondition.unenchantedChance (float)
       • LootItemRandomChanceWithLootingCondition.probability + lootingMultiplier (float)
     ★ Mixin 面积极小：约 3 个 Accessor 接口，≤ 30 行代码

  ⚠️ 不可静态求值的条件 — entity_properties (火焰/装备/生物群系/时间等)
     → 保守策略：未识别条件统一乘 0.3 衰减因子
     → 可配置：price_overrides 手工覆盖

  ⚠️ tag entry 需等级联 — 如 creeper_drop_music_discs 需查 tag 文件
     → tag 可在数据包加载时一并解析，非 Mixin 工作

  ✅ 定价算法可行 — 期望产出 = rolls × 条件概率 × 权重概率 × 期望数量
                    Price = C / (期望产出)，截断到 [1, 64]

  ✅ 计算时机 — 数据包 reload 时一次性缓存，无运行时开销
""")

    print("=" * 72)
    print("定价示例汇总 (PRICE_MULTIPLIER = 16)")
    print()

    # 直接计算几个典型例子的价格
    examples = [
        ("僵尸 - 腐肉",     1.0 * 1.0 * 1.0 * 1.0,       "无条件，uniform(0,2)"),
        ("僵尸 - 铁锭",     1.0 * 1.0 * 0.025 * 1.0,      "kbp + RCEB 2.5%"),
        ("凋零骷髅 - 煤",   1.0 * 0.333 * 0.0,             "见下方详解"),
        ("凋零骷髅 - 头颅", 1.0 * 0.333 * 0.025 * 1.0,    "kbp + RCEB 2.5%"),
        ("苦力怕 - 火药",   1.0 * 1.0 * 1.0 * 1.0,        "无条件，uniform(0,2)"),
        ("烈焰人 - 烈焰棒", 1.0 * 1.0 * 1.0 * 1.0,        "无条件，固定 1"),
    ]

    for label, epk, note in examples:
        price = compute_price(epk)
        print(f"  {label:<28} {epk:>6.4f} /k → {price:>2} 绿宝石")

    print()
    print("注意：凋零骷髅 coal 在 count=-1..1，min 为 -1 表示有概率不产出。")
    print("      期望 (min+max)/2 = 0，实际财务意义为零。此条目应跳过(不设为可交易)。")
    print()

    # 完整僵尸表
    print("─" * 72)
    print("僵尸完整分析:")
    for r in analyze_loot_table(os.path.join(BASE, "zombie.json"))[1]:
        print(f"  {r['item']:<30} prob={r['effective_prob']:.4f}  exp/kill={r['expected_per_kill']:.3f}  → {compute_price(r['expected_per_kill']):>2} em")

    print()
    print("凋零骷髅完整分析:")
    for r in analyze_loot_table(os.path.join(BASE, "wither_skeleton.json"))[1]:
        print(f"  {r['item']:<30} prob={r['effective_prob']:.4f}  exp/kill={r['expected_per_kill']:.3f}  → {compute_price(r['expected_per_kill']):>2} em")

    print()
    print("苦力怕完整分析:")
    for r in analyze_loot_table(os.path.join(BASE, "creeper.json"))[1]:
        print(f"  {r['item']:<30} prob={r['effective_prob']:.4f}  exp/kill={r['expected_per_kill']:.3f}  → {compute_price(r['expected_per_kill']):>2} em")


if __name__ == "__main__":
    main()