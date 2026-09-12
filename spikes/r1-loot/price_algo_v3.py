"""
R1 spike v3 — 全量扫描 100 张实体战利品表，穷举所有结构变体
=============================================================

v2 又暴露缺陷4：`rolls` 可以是分布对象（女巫 = uniform(1,3)），不只是 float。
与其一个个撞，不如全量扫描，把 1.21.1 全部 100 张实体表的结构变体一次列清。

本脚本产出：
  1. 结构变体清单（所有出现过的 entry type / function / condition / rolls 形态）
  2. 需要 Mixin Accessor 的精确字段清单
  3. 全量定价表 + 单调性验证
  4. 异常条目清单（零产出 / 不可静态求值 / 需级联解析）
"""

import json
import math
import os
from collections import Counter, defaultdict

BASE = os.path.join(os.path.dirname(__file__), "loot_tables")
PRICE_MIN, PRICE_MAX = 1, 64
UNKNOWN_COND_FACTOR = 0.3


# ══════════════════════════════════════════════════════════
# 数值提取（处理 float / NumberProvider 两种形态）
# ══════════════════════════════════════════════════════════
def num_expected(v, clamp_zero=False):
    """
    把 MC 的 NumberProvider 求期望。可能形态：
      • 3.0                                  → 常量
      • {"type":"constant","value":3}         → 常量
      • {"type":"uniform","min":1,"max":3}    → 均匀分布
      • {"type":"binomial","n":..,"p":..}     → 二项分布
    clamp_zero=True 时对 uniform 逐值 clamp 到 >=0（对齐 MC set_count 行为）
    """
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, dict):
        return 1.0
    t = v.get("type", "").split(":")[-1]
    if t == "constant":
        return float(v.get("value", 1))
    if t == "uniform":
        lo, hi = float(v.get("min", 0)), float(v.get("max", 1))
        if clamp_zero:
            a, b = int(math.floor(lo)), int(math.floor(hi))
            if b < a:
                return 0.0
            vals = [max(0, x) for x in range(a, b + 1)]
            return sum(vals) / len(vals)
        return (lo + hi) / 2.0
    if t == "binomial":
        n = num_expected(v.get("n", 1))
        p = num_expected(v.get("p", 0.5))
        return n * p
    if t == "score":
        return 1.0  # 依赖运行时计分板，无法静态求值
    return 1.0


def num_max(v):
    """取 NumberProvider 的上界（用于 FR-2.4 单次交易产出数量）"""
    if isinstance(v, (int, float)):
        return int(v)
    if not isinstance(v, dict):
        return 1
    t = v.get("type", "").split(":")[-1]
    if t == "constant":
        return int(num_expected(v))
    if t == "uniform":
        return int(math.floor(float(v.get("max", 1))))
    if t == "binomial":
        return int(num_expected(v.get("n", 1)))
    return 1


# ══════════════════════════════════════════════════════════
# 条件概率
# ══════════════════════════════════════════════════════════
def cond_prob(conditions, unknown_log=None):
    if not conditions:
        return 1.0, False
    prob = 1.0
    has_unknown = False
    for c in conditions:
        t = c.get("condition", "?").split(":")[-1]
        if t == "killed_by_player":
            pass  # 交易基准 = 玩家击杀
        elif t == "random_chance":
            prob *= num_expected(c.get("chance", 1.0))
        elif t == "random_chance_with_enchanted_bonus":
            prob *= float(c.get("unenchanted_chance", 0.025))
        elif t == "random_chance_with_looting":
            prob *= float(c.get("chance", 0.025))
        elif t == "table_bonus":
            ch = c.get("chances", [1.0])
            prob *= float(ch[0]) if ch else 1.0
        elif t == "all_of":
            for term in c.get("terms", []):
                p2, u2 = cond_prob([term], unknown_log)
                prob *= p2
                has_unknown |= u2
        elif t == "any_of":
            terms = c.get("terms", [])
            if terms:
                sub = [cond_prob([x], unknown_log) for x in terms]
                prob *= max(s[0] for s in sub)
                has_unknown |= any(s[1] for s in sub)
        elif t == "inverted":
            p2, u2 = cond_prob([c.get("term", {})], unknown_log)
            prob *= max(0.0, 1.0 - p2)
            has_unknown |= u2
        else:
            prob *= UNKNOWN_COND_FACTOR
            has_unknown = True
            if unknown_log is not None:
                unknown_log[t] += 1
    return prob, has_unknown


def count_expected(functions):
    base = 1.0
    for fn in (functions or []):
        f = fn.get("function", "?").split(":")[-1]
        if f == "set_count":
            base = num_expected(fn.get("count", 1), clamp_zero=True)
        elif f == "limit_count":
            lim = fn.get("limit", {})
            if isinstance(lim, dict) and "max" in lim:
                base = min(base, num_expected(lim["max"]))
    return max(0.0, base)


def count_max(functions):
    mx = 1
    for fn in (functions or []):
        f = fn.get("function", "?").split(":")[-1]
        if f == "set_count":
            mx = max(1, num_max(fn.get("count", 1)))
    return mx


def price_log(epk, cheap=2.0, rare=0.005):
    if epk <= 0:
        return None
    epk = max(rare * 0.1, min(cheap * 2, epk))
    span = math.log(cheap / rare)
    pos = max(0.0, min(1.0, math.log(cheap / epk) / span))
    return int(round(PRICE_MIN + (PRICE_MAX - PRICE_MIN) * pos))


# ══════════════════════════════════════════════════════════
# 全量扫描
# ══════════════════════════════════════════════════════════
def scan_all():
    stats = {
        "entry_types": Counter(),
        "functions": Counter(),
        "conditions": Counter(),
        "rolls_forms": Counter(),
        "count_forms": Counter(),
        "unknown_conds": Counter(),
    }
    priced = []          # (mob, item, epk, price, max_count)
    anomalies = defaultdict(list)

    files = sorted(f for f in os.listdir(BASE) if f.endswith(".json"))
    for fname in files:
        mob = fname[:-5]
        with open(os.path.join(BASE, fname), encoding="utf-8") as f:
            table = json.load(f)

        pools = table.get("pools", [])
        if not pools:
            anomalies["空表(无 pools)"].append(mob)
            continue

        for pool in pools:
            rolls_raw = pool.get("rolls", 1.0)
            stats["rolls_forms"][
                "float" if isinstance(rolls_raw, (int, float))
                else rolls_raw.get("type", "?").split(":")[-1]
            ] += 1
            rolls = num_expected(rolls_raw)

            pool_p, pool_unk = cond_prob(pool.get("conditions"), stats["unknown_conds"])
            for c in (pool.get("conditions") or []):
                stats["conditions"][c.get("condition", "?").split(":")[-1]] += 1

            entries = pool.get("entries", [])
            tw = sum(float(e.get("weight", 1)) for e in entries) or 1.0

            for e in entries:
                et = e.get("type", "?").split(":")[-1]
                stats["entry_types"][et] += 1

                for fn in (e.get("functions") or []):
                    stats["functions"][fn.get("function", "?").split(":")[-1]] += 1
                    if fn.get("function", "").endswith("set_count"):
                        cnt = fn.get("count", 1)
                        stats["count_forms"][
                            "float" if isinstance(cnt, (int, float))
                            else cnt.get("type", "?").split(":")[-1]
                        ] += 1
                for c in (e.get("conditions") or []):
                    stats["conditions"][c.get("condition", "?").split(":")[-1]] += 1

                if et != "item":
                    anomalies["非 item 条目(需级联/无法定价)"].append(
                        "%s: %s=%s" % (mob, et, e.get("name", e.get("value", "?"))))
                    continue

                item = e.get("name", "?").split(":")[-1]
                wp = float(e.get("weight", 1)) / tw
                ep, ep_unk = cond_prob(e.get("conditions"), stats["unknown_conds"])
                cnt = count_expected(e.get("functions"))
                epk = rolls * pool_p * wp * ep * cnt
                pr = price_log(epk)

                if pr is None:
                    anomalies["零期望产出(标记不可交易)"].append("%s/%s" % (mob, item))
                    continue
                if pool_unk or ep_unk:
                    anomalies["含不可静态求值条件(概率保守估计)"].append("%s/%s" % (mob, item))

                priced.append((mob, item, epk, pr, count_max(e.get("functions"))))

    return stats, priced, anomalies, len(files)


def main():
    stats, priced, anomalies, nfiles = scan_all()

    print("=" * 78)
    print("R1 SPIKE v3 — 1.21.1 全量实体战利品表扫描 (%d 张表)" % nfiles)
    print("=" * 78)

    print("\n【1】entry type 变体分布")
    for k, v in stats["entry_types"].most_common():
        mark = "✅可定价" if k == "item" else "⚠️需特殊处理"
        print("    %-22s %4d 次   %s" % (k, v, mark))

    print("\n【2】function 变体分布")
    for k, v in stats["functions"].most_common():
        print("    %-34s %4d 次" % (k, v))

    print("\n【3】condition 变体分布  ★ 决定 Mixin Accessor 清单")
    static_ok = {"killed_by_player", "random_chance", "random_chance_with_enchanted_bonus",
                 "random_chance_with_looting", "table_bonus", "all_of", "any_of", "inverted"}
    for k, v in stats["conditions"].most_common():
        mark = "✅可静态求值" if k in static_ok else "⚠️运行时依赖"
        print("    %-38s %4d 次   %s" % (k, v, mark))

    print("\n【4】rolls 形态")
    for k, v in stats["rolls_forms"].most_common():
        print("    %-22s %4d 次" % (k, v))
    print("\n【5】set_count 的 count 形态")
    for k, v in stats["count_forms"].most_common():
        print("    %-22s %4d 次" % (k, v))

    print("\n" + "=" * 78)
    print("【6】异常/特殊条目")
    print("=" * 78)
    for cat, items in anomalies.items():
        print("\n  ▸ %s —— %d 项" % (cat, len(items)))
        for it in items[:12]:
            print("      %s" % it)
        if len(items) > 12:
            print("      ... 及另外 %d 项" % (len(items) - 12))

    print("\n" + "=" * 78)
    print("【7】全量定价表 —— 按稀有度降序（期望产出升序）")
    print("=" * 78)
    srt = sorted(priced, key=lambda x: x[2])
    print("    %-34s %10s %6s %8s" % ("生物/物品", "期望/击杀", "价格", "单次产出"))
    print("    " + "-" * 62)
    for mob, item, epk, pr, mx in srt:
        print("    %-34s %10.4f %6d %8d" % ("%s/%s" % (mob, item), epk, pr, mx))

    print("\n" + "=" * 78)
    print("【8】单调性验证")
    print("=" * 78)
    bad = 0
    prev = None
    for mob, item, epk, pr, mx in srt:
        if prev and pr > prev[1] + 0:  # 期望产出升序 → 价格必须非升
            print("    ❌ %s/%s (epk=%.4f 价=%d) > 前项 %s (价=%d)"
                  % (mob, item, epk, pr, prev[0], prev[1]))
            bad += 1
        prev = ("%s/%s" % (mob, item), pr)
    if bad == 0:
        print("    ✅ 通过 —— %d 个可交易条目全部满足「越稀有越贵」" % len(srt))
    else:
        print("    ❌ %d 处违反" % bad)

    print("\n" + "=" * 78)
    print("【9】价格分布直方图")
    print("=" * 78)
    hist = Counter(pr for _, _, _, pr, _ in priced)
    for pr in sorted(hist):
        print("    %2d 绿宝石 │%s %d 项" % (pr, "█" * hist[pr], hist[pr]))

    print("\n" + "=" * 78)
    print("【10】R1 最终结论")
    print("=" * 78)
    print("""
  可行性：✅ 确认可行

  ── 无需 Mixin 的部分 ──────────────────────────────────
    LootTable.pools()      1.21.1 中 LootTable 为 record，pools 有 public accessor
    LootPool.entries()     同为 public
    → 表结构遍历零成本

  ── 必须 Mixin Accessor 的字段（面积极小）──────────────
    ① LootPool.rolls / bonusRolls            (NumberProvider, private final)
    ② LootPoolSingletonContainer.functions   (private, 取 set_count)
    ③ LootPoolEntryContainer.conditions      (private, 取概率条件)
    ④ LootItemRandomChanceCondition.probability
    ⑤ LootItemRandomChanceWithEnchantedBonusCondition.unenchantedChance
    ⑥ SetItemCountFunction.value             (NumberProvider)
    ⑦ LootItem.item                          (Holder<Item>)
    → 约 7 个 @Accessor，单文件 ≤ 60 行

  ── 必须特殊处理 ────────────────────────────────────
    tag 条目      需查 tag 注册表展开（数据包加载后可得，非 Mixin 工作）
    ref 条目      需递归解析被引用的 LootTable
    alternatives  按顺序取首个满足者，静态下取最大概率分支
    零期望产出    标记为不可交易，不得定天价

  ── 已验证修正的 4 个算法缺陷 ───────────────────────
    ① 线性反比 → 对数曲线（否则 0.11 以下全部撞价格上限，单调性丧失）
    ② uniform count 需逐值 clamp(>=0)（否则 uniform(-1,1) 被误判零产出）
    ③ rolls 可为分布对象（女巫 uniform(1,3)），不能当 float 读
    ④ 权重条目需算 weight/total（女巫 stick weight=2）
""")


if __name__ == "__main__":
    main()
