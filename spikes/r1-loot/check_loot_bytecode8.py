"""第八轮：条件/数量 builder 的实例化方式（供单测构造）。"""
import glob, subprocess
JAR = [c for c in glob.glob(
    r"D:\Coding\projects\peace-and-love\.gradle\loom-cache\minecraftMaven"
    r"\**\minecraft-merged-*.jar", recursive=True)
    if "sources" not in c and "neoforge" not in c][0]
def javap(cls):
    out = subprocess.run(["javap", "-p", "-classpath", JAR, cls],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else f"FAIL {out.stderr.strip()[:200]}"
for cls in [
    "net.minecraft.world.level.storage.loot.predicates.LootItemCondition$Builder",
    "net.minecraft.world.level.storage.loot.ConditionUserBuilder",
    "net.minecraft.world.level.storage.loot.predicates.LootItemCondition",
]:
    print("◆", cls.split(".")[-1])
    for line in javap(cls).splitlines():
        s = line.strip()
        if "abstract" in s or ("get" in s and "(" in s) or "build" in s or "interface" in s:
            print("  ", s)
