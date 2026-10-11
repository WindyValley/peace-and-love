"""核对 final_pricing_128.json 的条目与 38 个已适配生物的关系。

目的：确定 Java LootTableScanner 的扫描范围与验收基线。
产出：
  1. 黄金 JSON 共多少条目、涉及多少实体；
  2. 落在 38 适配集合内的条目数（=Java 扫描应得出的条数）；
  3. 适配但黄金 JSON 里没有任何条目的生物（空表/无掉落）；
  4. 黄金 JSON 里有、但不在适配集合的实体（不应被 Java 扫描）。
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]  # repo root
GOLDEN = BASE / "spikes" / "design-verify" / "final_pricing_128.json"

GOAL = [
    "zombie", "zombie_villager", "husk", "drowned", "zombified_piglin",
    "skeleton", "wither_skeleton", "stray", "bogged", "giant",
    "spider", "cave_spider", "creeper", "ghast", "blaze", "witch",
    "slime", "magma_cube", "enderman", "endermite", "guardian",
    "elder_guardian", "illusioner", "ravager", "silverfish", "shulker",
    "phantom", "pillager", "vindicator", "evoker", "vex", "wither",
]
BRAIN = ["piglin", "piglin_brute", "hoglin", "zoglin", "warden", "breeze"]
ADAPTED = set(GOAL) | set(BRAIN)
assert len(GOAL) == 32 and len(BRAIN) == 6 and len(ADAPTED) == 38

data = json.loads(GOLDEN.read_text(encoding="utf-8"))
entries = data["entries"]
print(f"黄金 JSON 总条目: {len(entries)}")
print(f"params: {data['params']}  monotonic_violations={data['monotonic_violations']}")

entities = {}
for e in entries:
    entities.setdefault(e["entity"], []).append(e["item"])
print(f"涉及实体数: {len(entities)}")

inside = [e for e in entries if e["entity"] in ADAPTED]
outside = sorted(set(e["entity"] for e in entries) - ADAPTED)
no_loot = sorted(ADAPTED - set(entities))

print(f"\n落在 38 适配集合内的条目: {len(inside)}")
print(f"适配但黄金 JSON 无条目的生物 ({len(no_loot)}): {no_loot}")
print(f"黄金 JSON 有但不适配的实体 ({len(outside)}): {outside}")

# 每个适配生物的条目数
print("\n各适配生物条目数:")
for m in sorted(ADAPTED, key=lambda m: -len(entities.get(m, []))):
    items = entities.get(m, [])
    if items:
        print(f"  {m:20s} {len(items)}  {items}")

# 唯一性检查：同一 entity+item 是否出现多次
dupes = [(k, len(v)) for k, v in entities.items() if len(v) != len(set(v))]
print(f"\n同生物重复物品的条目: {dupes if dupes else '无'}")

# epk 范围与撞顶情况
prices = [e["price_128"] for e in inside]
print(f"\n适配子集价格: min={min(prices)} max={max(prices)} "
      f"撞128={sum(1 for p in prices if p>=128)} 撞1={sum(1 for p in prices if p<=1)}")
