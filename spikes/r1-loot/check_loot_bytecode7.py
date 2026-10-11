"""第七轮：取表路径补全。"""
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
    "net.minecraft.server.ReloadableServerRegistries$Holder",
    "net.minecraft.world.level.storage.loot.LootDataResolver",
    "net.minecraft.world.level.storage.loot.LootDataManager",
]:
    print("◆", cls)
    for line in javap(cls).splitlines():
        s = line.strip()
        if s.startswith(("public", "class", "final class", "abstract class", "interface")) and "(" in s or "getLoot" in s or s.startswith("public class") or s.startswith("public final class"):
            print("  ", s)
