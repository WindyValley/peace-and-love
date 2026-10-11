"""第九轮：构造含 enchantment 的 RegistryAccess 的工厂方法。"""
import glob, subprocess
JAR = [c for c in glob.glob(
    r"D:\Coding\projects\peace-and-love\.gradle\loom-cache\minecraftMaven"
    r"\**\minecraft-merged-*.jar", recursive=True)
    if "sources" not in c and "neoforge" not in c][0]
def javap(cls):
    out = subprocess.run(["javap", "-p", "-classpath", JAR, cls],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else f"FAIL {out.stderr.strip()[:200]}"
print(javap("net.minecraft.core.RegistryAccess"))
print("##### nested ImmutableRegistryAccess #####")
print(javap("net.minecraft.core.RegistryAccess$ImmutableRegistryAccess"))
