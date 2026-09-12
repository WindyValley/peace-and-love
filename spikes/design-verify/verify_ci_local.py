"""本地验证 CI workflow（不推 GitHub，只验证能在本地成立的项）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ok = True

# 1. YAML 语法
try:
    import yaml
    with open(ROOT / ".github/workflows/build.yml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    print("✅ YAML 语法正确")
    # 校验关键字段
    assert "jobs" in data and "build" in data["jobs"], "缺 jobs.build"
    steps = data["jobs"]["build"]["steps"]
    cmds = [s.get("run", "") for s in steps]
    assert any("./gradlew build" in c for c in cmds), "缺 gradlew build 步骤"
    print("✅ 含 ./gradlew build 步骤")
    java = [s for s in steps if s.get("uses", "").startswith("actions/setup-java")]
    assert java and java[0]["with"]["java-version"] == 21, "JDK 版本应为 21"
    print("✅ JDK 21 (temurin)")
except ImportError:
    print("⚠️ pyyaml 缺失，跳过 YAML 校验")
except AssertionError as e:
    print("❌", e)
    ok = False

# 2. wrapper jar 必须在库
import subprocess
r = subprocess.run(["git", "ls-files", "gradle/wrapper/gradle-wrapper.jar"],
                   cwd=ROOT, capture_output=True, text=True)
if r.stdout.strip():
    print("✅ gradle-wrapper.jar 已入库")
else:
    print("❌ gradle-wrapper.jar 未入库，CI 无法启动")
    ok = False

# 3. 产物路径与 workflow 中的 artifact 路径一致
fab = list((ROOT / "fabric/build/libs").glob("peaceandlove-*.jar")) if (ROOT / "fabric/build/libs").exists() else []
neo = list((ROOT / "neoforge/build/libs").glob("peaceandlove-*.jar")) if (ROOT / "neoforge/build/libs").exists() else []
if fab and neo:
    print(f"✅ 双端 jar 存在（fabric {len(fab)}, neoforge {len(neo)}）")
else:
    print("⚠️ 双端 jar 未找到（需先 ./gradlew build）")

print("\n" + ("=" * 50))
print("本地可验证项通过" if ok else "本地验证有失败项")
print("注意：『CI 在 GitHub 实际跑绿』需推送后验证，本地无法替代。")
