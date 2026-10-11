"""第四轮：复合条目继承链 + 条件复合类 accessor + bonus table 字段。"""
import glob, subprocess
JAR = [c for c in glob.glob(
    r"D:\Coding\projects\peace-and-love\.gradle\loom-cache\minecraftMaven"
    r"\**\minecraft-merged-*.jar", recursive=True)
    if "sources" not in c and "neoforge" not in c][0]
def javap(cls):
    out = subprocess.run(["javap", "-p", "-classpath", JAR, cls],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else f"FAIL {out.stderr.strip()[:150]}"
for cls in [
    "net.minecraft.world.level.storage.loot.entries.EmptyLootItem",
    "net.minecraft.world.level.storage.loot.entries.NestedLootTable",
    "net.minecraft.world.level.storage.loot.entries.TagEntry",
    "net.minecraft.world.level.storage.loot.entries.CompositeEntryBase",
    "net.minecraft.world.level.storage.loot.predicates.AllOfCondition",
    "net.minecraft.world.level.storage.loot.predicates.AnyOfCondition",
    "net.minecraft.world.level.storage.loot.predicates.BonusLevelTableCondition",
    "net.minecraft.world.level.storage.loot.predicates.CompositeLootItemCondition",
    "net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceCondition",
]:
    body = javap(cls)
    head = next((l for l in body.splitlines() if l.strip().startswith(("public class", "final class", "abstract class"))), "?")
    print("◆", cls.split(".")[-1], "→", head.strip().split("class ")[-1])
    for line in body.splitlines():
        s = line.strip()
        # 字段 + 无参/集合 accessor
        if (s.startswith(("private final", "protected final")) and "(" not in s) \
           or (s.startswith("public") and "()" in s and ("List" in s or "float" in s or "NumberProvider" in s)):
            print("    ", s)
