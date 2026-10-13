"""第五轮：实体→战利品表解析 API + 条件/池 builder 可用性。"""
import glob, subprocess
JAR = [c for c in glob.glob(
    r"D:\Coding\projects\peace-and-love\.gradle\loom-cache\minecraftMaven"
    r"\**\minecraft-merged-*.jar", recursive=True)
    if "sources" not in c and "neoforge" not in c][0]
def javap(cls):
    out = subprocess.run(["javap", "-p", "-classpath", JAR, cls],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else f"FAIL {out.stderr.strip()[:200]}"

for cls, needle in [
    ("net.minecraft.world.entity.EntityType", "LootTable"),
    ("net.minecraft.world.level.storage.loot.LootDataManager", "LootTable"),
]:
    print("◆", cls)
    for line in javap(cls).splitlines():
        if needle in line and "(" in line:
            print("  ", line.strip())

print("\n◆ 条件构造器/ builder 静态方法")
for cls in [
    "net.minecraft.world.level.storage.loot.predicates.LootItemKilledByPlayerCondition",
    "net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceWithEnchantedBonusCondition",
    "net.minecraft.world.level.storage.loot.predicates.LootItemRandomChanceCondition",
    "net.minecraft.world.level.storage.loot.LootPool$Builder",
]:
    print("--", cls.split(".")[-1])
    for line in javap(cls).splitlines():
        s = line.strip()
        if ("public" in s and "(" in s and ("static" in s or s.startswith("public "+cls.split('.')[-1]))) :
            print("  ", s)
