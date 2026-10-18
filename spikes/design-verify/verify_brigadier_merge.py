"""验证 Brigadier addChild 对同名节点的语义：合并还是覆盖/抛异常。

背景：ConfigCommand 注册 /pal（reload/whitelist 子树），InspectCommand 再注册
/pal（inspect 子树）。需要确认 Brigadier 对重复 literal 根是递归合并，
否则后者会覆盖前者、丢失 reload/whitelist。
"""
import os
import subprocess
import zipfile
from pathlib import Path

HOME = Path(os.environ["USERPROFILE"])
candidates = list((HOME / ".gradle/caches").rglob("brigadier-*.jar"))
candidates = [p for p in candidates if "sources" not in p.name]
assert candidates, "未找到 brigadier jar"
jar = sorted(candidates)[-1]
print("brigadier jar:", jar.name)

work = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "brig-check"
work.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(jar) as z:
    z.extract("com/mojang/brigadier/tree/CommandNode.class", work)

javap = Path(os.environ.get("JAVA_HOME", r"C:\Program Files\Zulu\zulu-25")) / "bin" / "javap.exe"
if not javap.exists():
    javap = "javap"
out = subprocess.run([str(javap), "-p", "-c",
                      str(work / "com/mojang/brigadier/tree/CommandNode.class")],
                     capture_output=True, text=True).stdout

# 截取 addChild 方法体
start = out.find("public void addChild")
end = out.find("\n\n", start)
body = out[start:end]
print(body)

# 语义判据：字节码里对已存在同名子节点应再调用一次 addChild（递归合并）
calls = body.count("addChild")
print("\n[判据] addChild 方法体内递归调用 addChild 次数:", calls - 1,
      "（>=1 即合并语义）")
print("[判据] 含 containsKey/getChildren 查询:",
      "containsKey" in body or "getChildren" in body)
