"""
R2 spike — 交易能力注入方案可行性分析
========================================

问题：如何让僵尸这类 Mob 具备「打开交易界面」的能力？
      两个方案的跨加载器（Fabric / NeoForge）成本差异有多大？

方法：从 1.21.1 server.jar + 官方 mappings 中提取真实的接口签名，
      量化每个方案需要实现的方法数、依赖的私有成员、跨端差异点。
      不靠猜，全部用字节码事实说话。
"""

import io
import json
import os
import re
import struct
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
R3 = os.path.join(os.path.dirname(BASE), "r3-ai")
SERVER_JAR = os.path.join(R3, "server-1.21.1.jar")
MAPPINGS = os.path.join(R3, "server_mappings.txt")


def parse_mappings(path):
    """解析官方 mappings，返回 {官方类名: (混淆名, {方法签名: 混淆名})}"""
    result = {}
    cur_class = cur_obf = None
    cur_members = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line[0].isspace():
                if cur_class:
                    result[cur_class] = (cur_obf, cur_members)
                m = re.match(r"^(\S+)\s*->\s*(\S+):", line.strip())
                if m:
                    cur_class, cur_obf, cur_members = m.group(1), m.group(2), {}
                else:
                    cur_class = None
            elif cur_class:
                s = line.strip()
                mm = re.match(r"^(?:\d+:\d+:)?(\S+)\s+(\w+)(\([^)]*\))\s*->\s*(\S+)$", s)
                if mm:
                    ret, name, args, obf = mm.groups()
                    cur_members[name + args] = (obf, ret)
                else:
                    fm = re.match(r"^(\S+)\s+(\w+)\s*->\s*(\S+)$", s)
                    if fm:
                        cur_members["field:" + fm.group(2)] = (fm.group(3), fm.group(1))
        if cur_class:
            result[cur_class] = (cur_obf, cur_members)
    return result


def open_inner_jar(path):
    z = zipfile.ZipFile(path)
    inner = [n for n in z.namelist() if n.endswith(".jar") and "server" in n]
    if inner:
        with z.open(inner[0]) as f:
            return zipfile.ZipFile(io.BytesIO(f.read()))
    return z


def read_class(jar, obf):
    try:
        return jar.read(obf.replace(".", "/") + ".class")
    except KeyError:
        return None


def parse_class(data):
    """返回 (是否interface, 声明方法列表[(名,描述符,是否abstract)], 父类, 接口列表)"""
    if not data or data[:4] != b"\xca\xfe\xba\xbe":
        return None
    pos = 8
    cpc = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    cp = {}
    i = 1
    while i < cpc:
        tag = data[pos]; pos += 1
        if tag == 1:
            ln = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            cp[i] = data[pos:pos + ln].decode("utf-8", "replace"); pos += ln
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = ("ref", struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        elif tag == 15:
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            cp[i] = ("ref2", struct.unpack(">HH", data[pos:pos + 4])); pos += 4
        elif tag in (5, 6):
            pos += 8; i += 1
        else:
            return None
        i += 1

    def cls_name(idx):
        v = cp.get(idx)
        if isinstance(v, tuple) and v[0] == "ref":
            return cp.get(v[1])
        return None

    access = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    is_iface = bool(access & 0x0200)
    this_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    super_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    ic = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    ifaces = []
    for _ in range(ic):
        ifaces.append(cls_name(struct.unpack(">H", data[pos:pos + 2])[0])); pos += 2

    fc = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    fields = []
    for _ in range(fc):
        facc = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        fn = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        fd = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        fields.append((fn, fd, facc))
        ac = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        for _ in range(ac):
            pos += 2
            al = struct.unpack(">I", data[pos:pos + 4])[0]; pos += 4 + al

    mc = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    methods = []
    for _ in range(mc):
        macc = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        mn = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        md = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        methods.append((mn, md, bool(macc & 0x0400), macc))
        ac = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        for _ in range(ac):
            pos += 2
            al = struct.unpack(">I", data[pos:pos + 4])[0]; pos += 4 + al

    return {
        "is_interface": is_iface,
        "this": cls_name(this_i),
        "super": cls_name(super_i),
        "interfaces": ifaces,
        "fields": fields,
        "methods": methods,
    }


def main():
    print("=" * 90)
    print("R2 SPIKE — 交易能力注入方案分析（1.21.1 真实字节码）")
    print("=" * 90)

    maps = parse_mappings(MAPPINGS)
    jar = open_inner_jar(SERVER_JAR)
    print("[*] 映射类数: %d" % len(maps))

    # ─────────────────────────────────────────────
    # 1. Merchant 接口到底要求实现什么？
    # ─────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("【1】方案 A 的核心：Merchant 接口需要实现哪些方法？")
    print("=" * 90)

    MERCHANT = "net.minecraft.world.item.trading.Merchant"
    if MERCHANT not in maps:
        print("  !! 未找到 Merchant 映射")
    else:
        obf, members = maps[MERCHANT]
        info = parse_class(read_class(jar, obf))
        print("  官方类名: %s" % MERCHANT)
        print("  混淆类名: %s" % obf)
        print("  是接口: %s" % info["is_interface"])
        print("\n  接口方法（官方名 → 混淆名）:")

        # 反查混淆名 → 官方名
        rev = {}
        for sig, (o, ret) in members.items():
            if not sig.startswith("field:"):
                rev[o] = (sig, ret)

        abstract_count = 0
        default_count = 0
        for mn, md, is_abs, acc in sorted(info["methods"]):
            official = rev.get(mn, ("?", "?"))
            kind = "abstract ★必须实现" if is_abs else "default  (可不覆写)"
            if is_abs:
                abstract_count += 1
            else:
                default_count += 1
            print("    %-6s %-46s %s" % (mn, official[0], kind))

        print("\n  ▸ 必须实现的 abstract 方法: %d 个" % abstract_count)
        print("  ▸ 有默认实现的方法:        %d 个" % default_count)

    # ─────────────────────────────────────────────
    # 2. MerchantMenu 的构造依赖
    # ─────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("【2】方案 A 的第二步：MerchantMenu 构造需要什么？")
    print("=" * 90)
    MM = "net.minecraft.world.inventory.MerchantMenu"
    if MM in maps:
        obf, members = maps[MM]
        info = parse_class(read_class(jar, obf))
        print("  %s → %s" % (MM, obf))
        print("\n  构造器签名:")
        for mn, md, is_abs, acc in info["methods"]:
            if mn == "<init>":
                print("    %s" % md)
        print("\n  字段（private 需 Accessor 的用 ★ 标注）:")
        rev_f = {}
        for sig, (o, ret) in members.items():
            if sig.startswith("field:"):
                rev_f[o] = (sig[6:], ret)
        for fn, fd, facc in info["fields"]:
            is_priv = bool(facc & 0x0002)
            off = rev_f.get(fn, ("?", "?"))
            print("    %-6s %-24s %-38s %s" % (fn, off[0], off[1][:36], "★private" if is_priv else "public"))

    # ─────────────────────────────────────────────
    # 3. Villager 是怎么做的？（参考实现）
    # ─────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("【3】原版参考：Villager 如何实现 Merchant？")
    print("=" * 90)
    for cls in ["net.minecraft.world.entity.npc.AbstractVillager",
                "net.minecraft.world.entity.npc.Villager"]:
        if cls in maps:
            obf, members = maps[cls]
            info = parse_class(read_class(jar, obf))
            print("\n  %s → %s" % (cls.rsplit(".", 1)[-1], obf))
            print("    父类: %s" % info["super"])
            print("    实现接口: %s" % (info["interfaces"] or "无"))
            merch_obf = maps.get(MERCHANT, ("?", {}))[0]
            if merch_obf in (info["interfaces"] or []):
                print("    ✅ 直接实现 Merchant")

    # ─────────────────────────────────────────────
    # 4. Mob 类现状 —— 注入目标
    # ─────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("【4】注入目标：Mob 类的继承结构")
    print("=" * 90)
    for cls in ["net.minecraft.world.entity.Mob",
                "net.minecraft.world.entity.PathfinderMob",
                "net.minecraft.world.entity.monster.Monster",
                "net.minecraft.world.entity.monster.Zombie"]:
        if cls in maps:
            obf, _ = maps[cls]
            info = parse_class(read_class(jar, obf))
            print("  %-22s → %-6s  父类=%-8s 接口数=%d" % (
                cls.rsplit(".", 1)[-1], obf, info["super"], len(info["interfaces"] or [])))

    # ─────────────────────────────────────────────
    # 5. 方案 B 需要的组件
    # ─────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("【5】方案 B：自建 Menu 需要哪些原版组件？")
    print("=" * 90)
    for cls, why in [
        ("net.minecraft.world.inventory.AbstractContainerMenu", "自建 Menu 的父类"),
        ("net.minecraft.world.inventory.MenuType", "注册 MenuType"),
        ("net.minecraft.world.item.trading.MerchantOffer", "复用交易报价数据结构"),
        ("net.minecraft.world.item.trading.MerchantOffers", "报价列表"),
        ("net.minecraft.world.inventory.ContainerLevelAccess", "服务端位置校验"),
    ]:
        if cls in maps:
            obf, members = maps[cls]
            info = parse_class(read_class(jar, obf))
            n_pub = sum(1 for _, _, _, a in info["methods"] if a & 0x0001)
            print("  %-46s → %-6s  %s" % (cls.rsplit(".", 1)[-1], obf, why))

    # ─────────────────────────────────────────────
    # 6. MerchantOffer 的数据结构（两方案都要用）
    # ─────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("【6】MerchantOffer 数据结构（定价结果的载体）")
    print("=" * 90)
    MO = "net.minecraft.world.item.trading.MerchantOffer"
    if MO in maps:
        obf, members = maps[MO]
        info = parse_class(read_class(jar, obf))
        rev_f = {o: (s[6:], r) for s, (o, r) in members.items() if s.startswith("field:")}
        print("  %s → %s" % (MO, obf))
        print("\n  字段:")
        for fn, fd, facc in info["fields"]:
            off, typ = rev_f.get(fn, ("?", "?"))
            priv = "private" if facc & 0x0002 else "public "
            print("    %-6s %-22s %-30s %s" % (fn, off, typ[:28], priv))
        print("\n  构造器:")
        for mn, md, _, _ in info["methods"]:
            if mn == "<init>":
                print("    %s" % md[:100])

    # ─────────────────────────────────────────────
    # 结论
    # ─────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("【7】R2 结论")
    print("=" * 90)
    print("""
  ── 方案 A：Mixin 注入 Merchant 接口到 Mob ──────────────────────
    做法：@Mixin(Mob.class) + @Implements/接口注入，实现 Merchant 的全部 abstract 方法，
          openTradingScreen 复用原版 MerchantMenu

    ✅ 优点
       • GUI 零工作量 —— 完全复用原版村民界面与网络同步
       • 客户端可能无需装模组（走原版 Menu 与原版包）
       • MerchantOffer 的价格/次数/补货语义原版已实现（含 uses/maxUses）

    ❌ 缺点
       • 需给 Mob 注入接口 —— Fabric 用 Mixin 接口注入，
         NeoForge 需确认其 Mixin 配置与 AT (Access Transformer) 支持
       • Mob 是极高频基类，注入影响所有生物（含友好生物），需运行时判定
       • Architectury common 模块无法承载此注入（涉及混淆类字节码），
         需在 fabric / neoforge 各自模块重复

  ── 方案 B：自建 MenuType + 自定义网络包 ────────────────────────
    做法：注册自己的 MenuType，写自己的 ContainerMenu + Screen，
          用自定义包同步价格与交易结果

    ✅ 优点
       • 跨端一致 —— MenuType 注册在 Architectury 有统一 API，common 模块可承载大部分逻辑
       • 完全掌控界面与校验逻辑（FR-2.2 强制关闭 + 退货更容易实现）
       • 不污染 Mob 基类

    ❌ 缺点
       • 需自写 Screen（贴图 + 布局 + 滚动）
       • 需自写网络包与同步逻辑
       • 客户端必须安装模组

  ── 建议（待 design 阶段最终裁定）─────────────────────────────
    倾向 方案 B。理由：
      1. 本模组已确定「双端 + 服务器」，客户端必装模组不是额外负担
      2. FR-2.2 要求「交易中转敌对 → 强制关闭 + 退货」，自建 Menu 实现更干净
      3. Architectury 的 MenuType 注册有统一 API，common 模块能承载主体逻辑，
         而方案 A 的接口注入恰恰是 Architectury 无法屏蔽的部分
      4. 长期可维护性：不动 Mob 基类，与其他模组冲突面小得多

    ⚠️ 但方案 B 的 Screen 工作量需实际写一遍才能确认，
       建议 design 阶段做一个最小可运行原型（真机打开界面）再最终定案
""")


if __name__ == "__main__":
    main()
