"""第二轮核对：public accessor、NumberProvider、条件子类的真实类名/方法。"""
import glob
import subprocess
import zipfile

JAR = glob.glob(
    r"D:\Coding\projects\peace-and-love\.gradle\loom-cache\minecraftMaven"
    r"\**\minecraft-merged-*.jar", recursive=True)
JAR = [c for c in JAR if "sources" not in c and "neoforge" not in c][0]

def javap(cls, *opts):
    out = subprocess.run(["javap", "-p", "-classpath", JAR, cls, *opts],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else f"FAIL: {out.stderr.strip()[:200]}"

# 1) 列出 predicates / providers.number 包里所有类
with zipfile.ZipFile(JAR) as z:
    names = z.namelist()
for pkg in ["loot/predicates", "loot/providers/number", "loot/entries"]:
    print("=" * 80)
    print("PACKAGE", pkg)
    print("=" * 80)
    for n in sorted(names):
        if f"storage/loot/{pkg}/" in n and n.endswith(".class") and "$" not in n:
            print("  ", n.split("/")[-1][:-6])

# 2) 关键类的完整 public 方法签名
for cls in [
    "net.minecraft.world.level.storage.loot.LootTable",
    "net.minecraft.world.level.storage.loot.LootPool",
    "net.minecraft.world.level.storage.loot.providers.number.ConstantValue",
    "net.minecraft.world.level.storage.loot.providers.number.UniformGenerator",
    "net.minecraft.world.level.storage.loot.providers.number.BinomialDistributionGenerator",
    "net.minecraft.world.level.storage.loot.providers.number.NumberProvider",
]:
    print("=" * 80); print(cls); print("=" * 80)
    body = javap(cls)
    for line in body.splitlines():
        s = line.strip()
        if ("(" in s and not s.startswith(("private", "static"))) or s.startswith("public class") \
                or s.startswith("public abstract class") or s.startswith("public final class") \
                or s.startswith("public interface"):
            print("  ", s)
