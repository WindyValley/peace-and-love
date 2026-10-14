#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PAL 构建产物固定核验器 —— 取代每次发布/部署前现拼的 unzip+javap+grep。

检查项（全部自动断言，PASS/FAIL 逐行输出，任一 FAIL 退出码 1）：
  1. zip 可读 + 条目概览
  2. 平台元数据版本（NeoForge mods.toml / Fabric fabric.mod.json）== 期望版本
  3. 关键类在位（入口、BuildFlags、核心 Mixin）
  4. 验证探针开关：javap 反汇编 PeaceAndLove.init()，
     on  => 方法体内必须有 JsonRpcService 启动调用（-PenableVerifyRpc=true）
     off => 方法体内零 JsonRpcService 引用（正式包常量折叠；
            注意常量池残留不算数，只看 init() 方法体）
  5. 过程产物不进 jar（.md / spikes/ / tests/）
  6. 可选 --compare <other.jar>：逐 zip 条目比 CRC32（不受时间戳影响），
     architectury 每次构建的注入目录（随机 hash 前缀 + PlatformMethods.class）
     默认忽略，可用 --strict-crc 改为报错。

用法：
  python verify_jar.py <jar> [--expect-version 0.0.4] [--expect-rpc on|off|any]
                   [--platform neoforge|fabric|auto] [--compare other.jar]
                   [--strict-crc]
"""
import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

PKG = "top/windyvalley/peaceandlove"
# 发布闸门关心的 Mixin（少而关键；新增拦截点时在这里登记）
KEY_MIXINS = [
    "MobMerchantMixin",
    "HurtByTargetGoalMixin",
    "BrainMixin",
    "LivingEntityHurtMixin",
    "WitherBossMixin",
    "ZombifiedPiglinMixin",
]
JUNK_PATTERNS = [r"\.md$", r"(^|/)spikes/", r"(^|/)tests/", r"/_temp/"]

results = []  # (ok, label, detail)


def check(ok, label, detail=""):
    results.append((bool(ok), label, detail))


def detect_platform(zf):
    names = set(zf.namelist())
    if "META-INF/neoforge.mods.toml" in names or "META-INF/mods.toml" in names:
        return "neoforge"
    if "fabric.mod.json" in names:
        return "fabric"
    return None


def read_metadata_version(zf, platform):
    """返回 (版本串, 来源说明)。NeoForge 的 ${file.jarVersion} 回退 MANIFEST。"""
    if platform == "fabric":
        meta = json.loads(zf.read("fabric.mod.json").decode("utf-8"))
        ver = meta.get("version", "")
        return (ver, "fabric.mod.json#version") if not ver.startswith("${") \
            else _manifest_version(zf)
    # NeoForge
    cand = [n for n in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml")
            if n in zf.namelist()]
    toml = zf.read(cand[0]).decode("utf-8", errors="replace")
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', toml, re.M)
    if not m:
        return None, cand[0]
    val = m.group(1)
    if val.startswith("${"):  # ${file.jarVersion} → MANIFEST Implementation-Version
        return _manifest_version(zf)
    return val, f"{cand[0]} version"


def _manifest_version(zf):
    try:
        mf = zf.read("META-INF/MANIFEST.MF").decode("utf-8", errors="replace")
    except KeyError:
        return None, "MANIFEST.MF 缺失"
    m = re.search(r"^Implementation-Version:\s*(.+)$", mf, re.M)
    return (m.group(1).strip(), "MANIFEST.MF Implementation-Version") if m \
        else (None, "MANIFEST.MF 无 Implementation-Version")


def javap_init_body(jar):
    """javap 反汇编入口类，返回 init() 方法体指令行列表。

    javap 排版：方法签名 2 空格缩进，方法体指令 >=4 空格缩进，
    字段声明 2 空格缩进但无指令体；类结束 '}' 0 缩进。
    只收 init() 签名之后、下一个 2 空格顶层声明之前的深缩进行。
    """
    cls = PKG.replace("/", ".") + ".PeaceAndLove"
    p = subprocess.run(
        ["javap", "-cp", str(jar), "-c", "-p", cls],
        capture_output=True, timeout=60)
    if p.returncode != 0:
        # Windows 中文版 javap 可能输出 GBK；我们只搜 ASCII 符号，容错解码即可
        raise RuntimeError(p.stderr.decode("utf-8", errors="replace").strip()
                           or "javap 失败")
    out = p.stdout.decode("utf-8", errors="replace")
    lines = out.splitlines()
    body, in_init = [], False
    for ln in lines:
        if re.match(r"^\s+\S.*\binit\(\);\s*$", ln):
            in_init = True
            continue
        if in_init:
            if re.match(r"^ {0,3}\S", ln):  # 下一个顶层声明（2 空格签名/0 空格 }）
                break
            if ln.startswith("    "):       # 指令/行号表
                body.append(ln)
    if not body:
        raise RuntimeError("未找到 init() 方法体（入口类是否被重构？）")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jar", type=Path)
    ap.add_argument("--expect-version")
    ap.add_argument("--expect-rpc", choices=["on", "off", "any"], default="any")
    ap.add_argument("--platform", choices=["neoforge", "fabric", "auto"],
                    default="auto")
    ap.add_argument("--compare", type=Path)
    ap.add_argument("--strict-crc", action="store_true",
                    help="CRC 比对时不忽略 architectury 注入目录差异")
    args = ap.parse_args()

    if not args.jar.exists():
        sys.exit(f"找不到 jar: {args.jar}")

    print(f"== 核验 {args.jar.name} ==")
    try:
        zf = zipfile.ZipFile(args.jar)
        bad = zf.testzip()
        check(bad is None, "zip 完整性", "" if bad is None else f"损坏条目 {bad}")
    except zipfile.BadZipFile as e:
        sys.exit(f"不是合法 zip/jar: {e}")

    names = zf.namelist()
    classes = [n for n in names if n.endswith(".class")]
    print(f"   条目 {len(names)}（class {len(classes)}）")

    # 2) 平台与版本
    auto_platform = detect_platform(zf)
    platform = auto_platform if args.platform == "auto" else args.platform
    check(auto_platform is not None, "平台元数据存在",
          "" if auto_platform else "既无 mods.toml 也无 fabric.mod.json")
    if platform:
        if args.platform != "auto" and auto_platform != args.platform:
            check(False, f"平台 == {args.platform}", f"实际 {auto_platform}")
        else:
            check(True, f"平台 = {platform}")
        ver, src = read_metadata_version(zf, platform)
        if args.expect_version:
            check(ver == args.expect_version, f"版本 == {args.expect_version}",
                  f"实际 {ver!r}（{src}）")
        else:
            print(f"   版本 {ver!r}（{src}，未传 --expect-version 不比对）")

    # 3) 关键类在位（按简单类名匹配，容忍 architectury 注入目录前缀差异）
    entry_simple = {n.rsplit("/", 1)[-1]: n for n in names}
    for simple in ["PeaceAndLove.class", "BuildFlags.class"]:
        check(simple in entry_simple, f"关键类 {simple}",
              entry_simple.get(simple, "缺失"))
    for mixin in KEY_MIXINS:
        simple = mixin + ".class"
        check(simple in entry_simple, f"Mixin {mixin}",
              entry_simple.get(simple, "缺失"))

    # 4) 探针开关：数 init() 方法体内 SERVER_STARTING/STOPPED 的注册 invokedynamic
    #    坑（0.0.4 发布回核实证）：不能数 JsonRpcService 调用——
    #    启动代码在 lambda$init$1 合成方法里，javac 常量折叠只删 init() 内
    #    if(BuildFlags.ENABLE_VERIFY_RPC){...} 整块，死 lambda 方法仍保留
    #    new JsonRpcService().start()，但永不注册、运行时不执行。
    #    init() 内注册调用的注释类型是 LifecycleEvent$ServerState，on=2 / off=0。
    if args.expect_rpc != "any":
        try:
            body = javap_init_body(args.jar)
            regs = [ln.strip() for ln in body
                    if "LifecycleEvent$ServerState" in ln]
            n = len(regs)
            if args.expect_rpc == "on":
                check(n >= 2, "探针生命周期注册 >= 2（RPC 构建）",
                      f"{n} 条" if n else "init() 内无 SERVER_STARTING/STOPPED 注册，开关没生效？")
            else:
                check(n == 0, "探针生命周期注册 == 0（正式构建折叠）",
                      "" if n == 0 else "\n       ".join(regs[:5]))
        except RuntimeError as e:
            check(False, "javap 反汇编入口类", str(e).splitlines()[0][:160])

    # 5) 过程产物
    junk = [n for n in names
            if any(re.search(p, n) for p in JUNK_PATTERNS)]
    check(not junk, "无过程产物（.md/spikes/tests/_temp）",
          ", ".join(junk[:5]) if junk else "")

    # 6) 可选 CRC 比对
    if args.compare:
        if not args.compare.exists():
            check(False, f"比对对象存在 {args.compare.name}")
        else:
            with zipfile.ZipFile(args.compare) as z2:
                a = {i.filename: i.CRC for i in zf.infolist()}
                b = {i.filename: i.CRC for i in z2.infolist()}
            injected = lambda n: ("PlatformMethods" in n
                                  or "/architectury/" in n
                                  or re.search(r"/[0-9a-f]{8,}/", n))
            only_a = sorted(set(a) - set(b))
            only_b = sorted(set(b) - set(a))
            crc_diff = sorted(n for n in set(a) & set(b) if a[n] != b[n])
            if not args.strict_crc:
                ia = [n for n in only_a if injected(n)]
                ib = [n for n in only_b if injected(n)]
                only_a, only_b = [n for n in only_a if n not in ia], \
                                 [n for n in only_b if n not in ib]
                note = f"（已忽略 architectury 注入条目 {len(ia)+len(ib)} 个）"
            else:
                note = ""
            ok = not (only_a or only_b or crc_diff)
            detail = note
            if not ok:
                detail = "仅左有 %d / 仅右有 %d / CRC 不同 %d %s" % (
                    len(only_a), len(only_b), len(crc_diff), note)
            check(ok, f"CRC 与 {args.compare.name} 逐条目一致", detail)
            if not ok:
                for n in only_a[:8]:
                    print(f"       仅左: {n}")
                for n in only_b[:8]:
                    print(f"       仅右: {n}")
                for n in crc_diff[:8]:
                    print(f"       CRC差: {n}")

    # 汇总
    print("-" * 60)
    failed = 0
    for ok, label, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        line = f"[{mark}] {label}"
        if detail and not ok:
            line += f" —— {detail}"
        print(line)
    print("-" * 60)
    total = len(results)
    print(f"{total - failed}/{total} 通过")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
