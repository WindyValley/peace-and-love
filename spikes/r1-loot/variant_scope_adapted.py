"""列出 30 个「适配且有掉落」生物的战利品表实际用到的全部结构变体。

目的：给 Java LootTableScanner 的 instanceof/Accessor 清单划精确边界，
只实现真实出现过的变体，其余走「未知=0.3」保守分支。
同时定位 random_chance_with_looting 等条件的真实 JSON type 字符串。
"""
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent / "loot_tables"

ADAPTED_WITH_LOOT = [
    "zombie", "zombie_villager", "husk", "drowned", "zombified_piglin",
    "skeleton", "wither_skeleton", "stray", "bogged",
    "spider", "cave_spider", "creeper", "ghast", "blaze", "witch",
    "slime", "magma_cube", "enderman", "guardian", "elder_guardian",
    "ravager", "shulker", "phantom", "pillager", "vindicator", "evoker",
    "piglin",  # 黄金 JSON 无条目，但先确认表内容
    "hoglin", "zoglin", "warden", "breeze",
]

entry_types = Counter()
func_types = Counter()
cond_types = Counter()
roll_forms = Counter()
count_forms = Counter()
non_item = []

def walk_conditions(conds, where):
    for c in conds or []:
        t = c.get("condition", "?").split(":")[-1]
        cond_types[f"{t} @{where}"] += 1
        if t == "all_of" or t == "any_of":
            walk_conditions(c.get("terms"), where + "/" + t)
        elif t == "inverted":
            walk_conditions([c.get("term")], where + "/inverted")

def walk_entries(entries, mob, depth=0):
    for e in entries or []:
        t = e.get("type", "?").split(":")[-1]
        entry_types[t] += 1
        if t != "item":
            non_item.append(f"{mob}: {t} = {e.get('name', e.get('value', '?'))}")
        for fn in e.get("functions") or []:
            f = fn.get("function", "?").split(":")[-1]
            func_types[f] += 1
            if f == "set_count":
                c = fn.get("count", 1)
                form = "const" if isinstance(c, (int, float)) else c.get("type", "?").split(":")[-1]
                count_forms[form] += 1
        walk_conditions(e.get("conditions"), "entry")
        # 复合条目递归其 children
        for key in ("children", "entries"):
            if isinstance(e.get(key), list):
                walk_entries(e[key], mob, depth + 1)

tables_scanned = []
for mob in ADAPTED_WITH_LOOT:
    f = BASE / f"{mob}.json"
    if not f.exists():
        print(f"!! 缺表: {mob}.json")
        continue
    table = json.loads(f.read_text(encoding="utf-8"))
    pools = table.get("pools")
    if not pools:
        print(f"-- 无 pools: {mob} (keys={list(table.keys())})")
        continue
    tables_scanned.append(mob)
    for pool in pools:
        r = pool.get("rolls", 1.0)
        roll_forms["const" if isinstance(r, (int, float)) else r.get("type", "?").split(":")[-1]] += 1
        walk_conditions(pool.get("conditions"), "pool")
        walk_entries(pool.get("entries"), mob)

print(f"\n扫描 {len(tables_scanned)} 张有 pools 的表\n")
print("ENTRY 类型:")
for k, v in entry_types.most_common(): print(f"  {k:30s} {v}")
print("\nFUNCTION 类型:")
for k, v in func_types.most_common(): print(f"  {k:34s} {v}")
print("\nCONDITION 类型:")
for k, v in cond_types.most_common(): print(f"  {k:44s} {v}")
print("\nROLLS 形态:")
for k, v in roll_forms.most_common(): print(f"  {k:20s} {v}")
print("\nSET_COUNT count 形态:")
for k, v in count_forms.most_common(): print(f"  {k:20s} {v}")
print("\n非 item 条目:")
for x in non_item: print("  ", x)
