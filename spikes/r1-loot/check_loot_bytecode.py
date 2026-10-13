"""字节码核对战利品表相关类的真实字段/方法名（1.21.1 mojang mappings）。

spike 列了 7 个必须 @Accessor 的字段，但字段名不能凭记忆 —— 用 javap 逐类核对。
只查 private/包级 final 字段（Mixin @Accessor 目标）。
"""
import subprocess
import sys

JAR = (r"D:\Coding\projects\peace-and-love\.gradle\loom-cache\minecraftMaven"
       r"\net\minecraft\minecraft-merged-2648a56825"
       r"\1.21.1-loom.mappings.1_21_1.layered+hash.40359-v2"
       r"\minecraft-merged-2648a56825-1.21.1-loom.mappings.1_21_1.layered+hash.40359-v2.jar")
import os
if not os.path.exists(JAR):
    # 兜底：在项目 loom-cache 里找任意非 sources 的 named merged jar
    import glob
    cands = glob.glob(r"D:\Coding\projects\peace-and-love\.gradle\loom-cache"
                      r"\minecraftMaven\**\minecraft-merged-*.jar", recursive=True)
    cands = [c for c in cands if "sources" not in c and "neoforge" not in c]
    JAR = cands[0]
    print("USING FALLBACK JAR:", JAR)

CLASSES = [
    "net.minecraft.world.level.storage.loot.LootTable",
    "net.minecraft.world.level.storage.loot.LootPool",
    "net.minecraft.world.level.storage.loot.entries.LootPoolEntryContainer",
    "net.minecraft.world.level.storage.loot.entries.LootPoolSingletonContainer",
    "net.minecraft.world.level.storage.loot.entries.LootItem",
    "net.minecraft.world.level.storage.loot.functions.SetItemCountFunction",
    "net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceCondition",
    "net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceWithEnchantedBonusCondition",
    "net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceWithLootingCondition",
]

for cls in CLASSES:
    print("=" * 90)
    print(cls)
    print("=" * 90)
    out = subprocess.run(
        ["javap", "-p", "-classpath", JAR, cls],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        print("  !! JAVAP FAILED:", out.stderr.strip()[:300])
        continue
    for line in out.stdout.splitlines():
        s = line.strip()
        # 只看字段（含 private/final），过滤掉方法与 class 声明行
        if s.startswith(("private", "final", "protected", "volatile", "transient")) \
                and "(" not in s and "class " not in s and "interface " not in s:
            print("  FIELD:", s)
        elif s.startswith("public") and "(" not in s and "class " not in s:
            print("  pubfield?:", s)
    # record 组件（public accessor）单独看 LootTable/LootPool
    if cls.endswith(("LootTable", "LootPool")):
        recs = [l.strip() for l in out.stdout.splitlines()
                if l.strip().startswith("public") and "(" in l and "()" in l]
        print("  -- public 无参方法(record accessor 候选) --")
        for r in recs[:25]:
            print("   ", r)
