"""
核实：1.21.1 server.jar 是 bundler 结构，真正代码在
META-INF/versions/1.21.1/server-1.21.1.jar 内。

先前 R2/R3 的分析是否用了正确的 jar？本脚本重新用内层 jar 验证，
并与先前结论对照。
"""
import io
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTER = BASE.parent / "r3-ai" / "server-1.21.1.jar"
INNER_ENTRY = "META-INF/versions/1.21.1/server-1.21.1.jar"


def get_inner():
    z = zipfile.ZipFile(OUTER)
    data = z.read(INNER_ENTRY)
    return zipfile.ZipFile(io.BytesIO(data))


def main():
    print("=" * 80)
    print("核实 jar 结构与先前分析的一致性")
    print("=" * 80)

    outer = zipfile.ZipFile(OUTER)
    print(f"\n外层 jar：{len(outer.namelist())} 个条目（bundler 壳）")

    inner = get_inner()
    inames = inner.namelist()
    print(f"内层 jar：{len(inames)} 个条目（真正的 MC 代码）")

    classes = [n for n in inames if n.endswith(".class")]
    print(f"  其中 .class 文件：{len(classes)} 个")

    print("\n--- 检查关键混淆类是否在内层 jar ---")
    for c in ["dbu", "dbt", "cmk", "cmf"]:
        entry = f"{c}.class"
        status = "✅ 存在" if entry in inames else "❌ 缺失"
        print(f"  {entry:14} {status}")

    print("\n--- 内层 jar 顶层结构 ---")
    import collections
    cc = collections.Counter(
        n.split("/")[0] if "/" in n else "(根目录 .class)"
        for n in inames
    )
    for k, v in cc.most_common(10):
        print(f"  {v:7}  {k}")

    print("\n" + "=" * 80)
    print("结论")
    print("=" * 80)
    root_classes = [n for n in classes if "/" not in n]
    print(f"""
  混淆后的 MC 类位于内层 jar 的**根目录**，共 {len(root_classes)} 个 .class。

  ⚠️ 先前 R2/R3 脚本直接对外层 jar 调用 zf.read('dbu.class') 会失败。
     需要确认那些脚本当时是如何拿到数据的 —— 若同样失败，
     则先前「Merchant 有 3 个 default 方法」等结论**不可信**，必须重跑。
""")


if __name__ == "__main__":
    main()
