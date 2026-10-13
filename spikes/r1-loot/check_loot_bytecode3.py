"""第三轮：列 predicates/functions/entries/number 包类名 + 关键类访问器。"""
import glob
import subprocess
import zipfile

JAR = [c for c in glob.glob(
    r"D:\Coding\projects\peace-and-love\.gradle\loom-cache\minecraftMaven"
    r"\**\minecraft-merged-*.jar", recursive=True)
    if "sources" not in c and "neoforge" not in c][0]

def javap(cls):
    out = subprocess.run(["javap", "-p", "-classpath", JAR, cls],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else f"FAIL {out.stderr.strip()[:150]}"

with zipfile.ZipFile(JAR) as z:
    names = z.namelist()
for sub in ["predicates", "functions", "providers/number"]:
    pkg = f"net/minecraft/world/level/storage/loot/{sub}/"
    found = sorted(n.split("/")[-1][:-6] for n in names
                   if n.startswith(pkg) and n.endswith(".class") and "$" not in n)
    print(f"== {sub} ({len(found)}) ==")
    print("  " + ", ".join(found))
pkg = "net/minecraft/world/level/storage/loot/entries/"
found = sorted(n.split("/")[-1][:-6] for n in names
               if n.startswith(pkg) and n.endswith(".class") and "$" not in n)
print(f"== entries ({len(found)}) ==")
print("  " + ", ".join(found))

print("\n##### 关键类成员 #####")
for cls in [
    "net.minecraft.world.level.storage.loot.predicates.InvertedLootItemCondition",
    "net.minecraft.world.level.storage.loot.predicates.LootItemTableBonusCondition",
    "net.minecraft.world.level.storage.loot.entries.LootPoolSingletonContainer",
    "net.minecraft.world.level.storage.loot.entries.LootItem",
    "net.minecraft.world.level.storage.loot.functions.SetItemCountFunction",
    "net.minecraft.world.level.storage.loot.functions.LimitCountFunction",
    "net.minecraft.world.level.storage.loot.providers.number.ScoreboardValue",
]:
    print("=" * 80); print(cls.split(".")[-1])
    for line in javap(cls).splitlines():
        s = line.strip()
        if s.startswith(("private", "protected", "public")) and "class " not in s:
            print("  ", s)
