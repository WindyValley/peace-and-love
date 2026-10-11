"""第六轮：取表 API（LootDataManager / ReloadableServerRegistries / MinecraftServer）。"""
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
    "net.minecraft.world.level.storage.loot.LootDataManager",
    "net.minecraft.server.ReloadableServerRegistries",
]:
    print("◆", cls)
    for line in javap(cls).splitlines():
        s = line.strip()
        if "public" in s and "(" in s:
            print("  ", s)
print("◆ MinecraftServer (loot 相关)")
for line in javap("net.minecraft.server.MinecraftServer").splitlines():
    if "Loot" in line or "reloadableRegistries" in line:
        print("  ", line.strip())
