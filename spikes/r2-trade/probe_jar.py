"""排查：1.21.1 server.jar 的实际结构，找出混淆类真实路径。"""
import collections
import zipfile
from pathlib import Path

JAR = Path(__file__).resolve().parent.parent / "r3-ai" / "server-1.21.1.jar"

z = zipfile.ZipFile(JAR)
names = z.namelist()
print("total entries:", len(names))

print("\n--- 顶层目录分布 ---")
c = collections.Counter(n.split("/")[0] for n in names)
for k, v in c.most_common(15):
    print(f"  {v:7}  {k}")

print("\n--- 查找 dbu.class / dbt.class ---")
hits = [n for n in names if n.endswith("dbu.class") or n.endswith("dbt.class")]
print("  ", hits if hits else "未找到")

print("\n--- 嵌套 jar？ ---")
inner = [n for n in names if n.endswith(".jar")]
for n in inner[:20]:
    print("  ", n)

print("\n--- versions/ 下内容 ---")
for n in names:
    if n.startswith("META-INF/versions/") and n.endswith(".jar"):
        print("  ", n)
