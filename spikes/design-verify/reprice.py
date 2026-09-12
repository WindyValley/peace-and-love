"""
重算定价表 —— PRICE_MAX = 128（用户最终决策）
================================================
复用 r1-loot/price_algo_v3.py 中已验证的战利品表解析与 epk 计算，
仅把 PRICE_MAX 从 64 改为 128，产出 design 文档要引用的最终数字。

同时产出 adapted_mobs 的完整交易规格 JSON，供 dev 阶段直接使用。
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
R1 = BASE.parent / "r1-loot"

spec = importlib.util.spec_from_file_location("pa3", R1 / "price_algo_v3.py")
pa3 = importlib.util.module_from_spec(spec)
sys.modules["pa3"] = pa3
# price_algo_v3 的相对路径依赖：切到它的目录
import os
old = os.getcwd()
os.chdir(R1)
try:
    spec.loader.exec_module(pa3)
finally:
    os.chdir(old)

# ── 覆盖为最终决策值 ──
PRICE_MIN, PRICE_MAX = 1, 128
EPK_CHEAP, EPK_RARE = 2.0, 0.005


def price_log(epk, cheap=EPK_CHEAP, rare=EPK_RARE):
    if epk <= 0:
        return PRICE_MAX
    if epk >= cheap:
        return PRICE_MIN
    if epk <= rare:
        return PRICE_MAX
    pos = math.log(cheap / epk) / math.log(cheap / rare)
    return int(round(PRICE_MIN + (PRICE_MAX - PRICE_MIN) * pos))


os.chdir(R1)
try:
    stats, priced, anomalies, nfiles = pa3.scan_all()
finally:
    os.chdir(old)

print("=" * 78)
print("最终定价表 —— PRICE_MAX = 128, cheap = 2.0, rare = 0.005")
print("=" * 78)
print(f"\n扫描 {nfiles} 张战利品表，得到 {len(priced)} 个可定价条目")
print("⚠️  priced 中的 price 是 PRICE_MAX=64 时算的，下面用 epk 全部重算")

# priced: (mob, item, epk, price_old, max_count)
out = []
for mob, item, epk, price_old, cnt_max in priced:
    out.append({
        "entity": mob,
        "item": item,
        "epk": epk,
        "price_64": price_old,
        "price_128": price_log(epk),
        "count_max": cnt_max,
    })

# 单调性校验
print("\n" + "=" * 78)
print("单调性校验（epk 越小 → 价格必须越高或相等）")
print("=" * 78)
s = sorted(out, key=lambda x: -x["epk"])
bad = 0
for a, b in zip(s, s[1:]):
    if b["price_128"] < a["price_128"]:
        bad += 1
        print(f"  ❌ {a.get('entity')}/{a.get('item')} epk={a['epk']:.4f} p={a['price_128']}"
              f"  >  {b.get('entity')}/{b.get('item')} epk={b['epk']:.4f} p={b['price_128']}")
print(f"\n结果：{len(out)} 个条目，{bad} 处违反单调性"
      f" —— {'✅ 全部通过' if bad == 0 else '❌ 存在问题'}")

# design 文档引用的代表性条目
print("\n" + "=" * 78)
print("design 文档引用的代表性定价")
print("=" * 78)
WANT = [
    ("zombie", "rotten_flesh"), ("zombie", "iron_ingot"),
    ("zombie", "carrot"), ("zombie", "potato"),
    ("skeleton", "bone"), ("skeleton", "arrow"),
    ("wither_skeleton", "skull"), ("wither_skeleton", "coal"),
    ("creeper", "gunpowder"), ("enderman", "ender_pearl"),
    ("spider", "string"), ("spider", "spider_eye"),
    ("drowned", "copper_ingot"), ("drowned", "trident"),
    ("blaze", "blaze_rod"), ("witch", "redstone"),
    ("slime", "slime_ball"), ("ghast", "ghast_tear"),
    ("guardian", "prismarine_shard"), ("shulker", "shulker_shell"),
    ("warden", "sculk_catalyst"), ("breeze", "breeze_rod"),
]
print(f"\n  {'生物':<20} {'物品':<24} {'epk':>9}  {'价格':>5}  {'单次产出':>8}")
print(f"  {'-'*20} {'-'*24} {'-'*9}  {'-'*5}  {'-'*8}")
for ent, itm in WANT:
    for r in out:
        e = str(r.get("entity", ""))
        i = str(r.get("item", ""))
        if e.endswith(ent) and i.endswith(itm):
            cnt = r.get("count_max", r.get("count", "?"))
            print(f"  {e.split(':')[-1]:<20} {i.split(':')[-1]:<24} "
                  f"{r['epk']:>9.4f}  {r['price_128']:>5}  {cnt:>8}")
            break

# 价格分布
print("\n" + "=" * 78)
print("价格分布")
print("=" * 78)
buckets = {}
for r in out:
    b = (r["price_128"] - 1) // 16 * 16 + 1
    buckets[b] = buckets.get(b, 0) + 1
for b in sorted(buckets):
    bar = "█" * buckets[b]
    print(f"  {b:>3}-{min(b+15, 128):>3} : {buckets[b]:>3}  {bar}")

hit_max = sum(1 for r in out if r["price_128"] >= PRICE_MAX)
hit_min = sum(1 for r in out if r["price_128"] <= PRICE_MIN)
print(f"\n  撞上限(128)：{hit_max} 个    撞下限(1)：{hit_min} 个")

# 落盘供 dev 阶段使用
dst = BASE / "final_pricing_128.json"
dst.write_text(json.dumps({
    "params": {"price_min": PRICE_MIN, "price_max": PRICE_MAX,
               "epk_cheap": EPK_CHEAP, "epk_rare": EPK_RARE},
    "monotonic_violations": bad,
    "entries": out,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n✅ 已写入 {dst.name}（{len(out)} 条）")
