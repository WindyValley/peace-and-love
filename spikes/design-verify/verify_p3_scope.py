"""
P3 验证 —— 注入 Mob 基类 vs 注入 38 个目标类的影响面
========================================================
这是静态问题，不需要跑服务端：直接扫描 MC jar 统计 Mob 的全部子类。

问题：ADR-002 选择「Mixin 注入 Mob 基类 + 运行时判定」。
      代价是所有 Mob 子类都会携带 Merchant 字段。
      到底波及多少个非目标生物？值不值得改成注入 38 个具体类？

统计：
  1. 原版 Mob 的全部子类（沿继承链）
  2. 其中可实例化的（非 abstract）
  3. 与 38 个已适配生物的差集 = 额外影响面
  4. 每实例内存开销估算
"""
import io
import struct
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
JAR = BASE.parent / "r3-ai" / "server-1.21.1.jar"

exec((BASE / "extract_api.py").read_text(encoding="utf-8").split(
    "def main():")[0].split('"""', 2)[2])

MOB = "net.minecraft.world.entity.Mob"
ACC_ABSTRACT = 0x0400


def main():
    n2o, o2n, members = load_mappings()
    zf = open_mc_jar(JAR)
    names = [n for n in zf.namelist() if n.endswith(".class")]

    mob_obf = n2o.get(MOB)
    mob_internal = mob_obf.replace(".", "/")
    print("=" * 78)
    print("P3 —— 注入 Mob 基类的影响面（静态分析）")
    print("=" * 78)
    print(f"\nMob 混淆名：{mob_obf}")

    # 一次性解析所有类
    # parse_class 不返回类级 access_flags，这里自己补读：
    #   ClassFile: magic(4) minor(2) major(2) constant_pool ... access_flags(2)
    # 常量池长度可变，最省事的办法是复用 parse_class 拿到 this/super，
    # 再单独扫一次常量池尾部取 access_flags。
    def read_access(data):
        off = 8
        cp_count = struct.unpack(">H", data[off:off + 2])[0]
        off += 2
        i = 1
        while i < cp_count:
            tag = data[off]
            off += 1
            if tag == 1:
                ln = struct.unpack(">H", data[off:off + 2])[0]
                off += 2 + ln
            else:
                _, size = CP_TAGS.get(tag, (None, None))
                if size is None:
                    return None
                off += size
                if tag in (5, 6):
                    i += 1
            i += 1
        return struct.unpack(">H", data[off:off + 2])[0]

    info_map = {}
    access_map = {}
    for entry in names:
        data = zf.read(entry)
        info = parse_class(data)
        if info:
            key = entry[:-6]
            info_map[key] = info
            try:
                access_map[key] = read_access(data) or 0
            except Exception:
                access_map[key] = 0
    print(f"jar 内类总数：{len(info_map)}")

    # 沿 super 链判定是否 Mob 子类
    cache = {}

    def is_mob(internal, depth=0):
        if depth > 20:
            return False
        if internal == mob_internal:
            return True
        if internal in cache:
            return cache[internal]
        info = info_map.get(internal)
        if not info or not info["super"]:
            cache[internal] = False
            return False
        r = is_mob(info["super"], depth + 1)
        cache[internal] = r
        return r

    subclasses = []
    for internal, info in info_map.items():
        if internal == mob_internal:
            continue
        if is_mob(internal):
            real = o2n.get(internal.replace("/", "."), internal)
            is_abs = bool(access_map.get(internal, 0) & ACC_ABSTRACT)
            subclasses.append((real, is_abs))

    concrete = [r for r, a in subclasses if not a]
    abstract = [r for r, a in subclasses if a]

    print(f"\nMob 的子类总数        : {len(subclasses)}")
    print(f"  其中 abstract        : {len(abstract)}")
    print(f"  其中可实例化(concrete): {len(concrete)}")

    # 已适配 38 个 —— JSON 只存 entity id，需转成类名
    import json
    import re as _re
    plan = json.loads((BASE.parent / "r3-ai" / "neutralization_plan_v3.json")
                      .read_text(encoding="utf-8"))
    adapted_ids = set()
    for m in plan["goal_system"] + plan["brain_system"]:
        if m["id"] != "ender_dragon":
            adapted_ids.add(m["id"])

    # 类名与 entity id 不一致的特例
    CLS_ID_FIX = {
        "WitherBoss": "wither",
        "EnderMan": "enderman",
        "SnowGolem": "snow_golem",
        "MushroomCow": "mooshroom",
    }

    def cls_simple_to_id(simple):
        """EnderMan -> enderman / ender_man 两种候选都返回"""
        if simple in CLS_ID_FIX:
            return {CLS_ID_FIX[simple]}
        snake = _re.sub(r"(?<!^)(?=[A-Z])", "_", simple).lower()
        return {snake, snake.replace("_", "")}

    print(f"\n本模组已适配（v1.0）  : {len(adapted_ids)}")

    matched_ids = set()
    extra = []
    for c in concrete:
        simple = c.split(".")[-1]
        cands = cls_simple_to_id(simple)
        hit = cands & adapted_ids
        if hit:
            matched_ids |= hit
        else:
            extra.append(c)

    extra.sort()
    print(f"  类名成功匹配上的      : {len(matched_ids)} / {len(adapted_ids)}")
    unmatched = adapted_ids - matched_ids
    if unmatched:
        print(f"  ⚠️ 未能由类名匹配的    : {sorted(unmatched)}")
    print(f"额外影响面（非目标）  : {len(extra)} 个可实例化 Mob 子类")

    print("\n  额外被注入的生物（前 40 个）：")
    for c in extra[:40]:
        print(f"      {c.split('.')[-1]}")
    if len(extra) > 40:
        print(f"      ... 及其余 {len(extra) - 40} 个")

    # 内存开销估算
    print("\n" + "=" * 78)
    print("内存开销估算")
    print("=" * 78)
    print("""
  注入的实例字段（design 方案）：
      Player          pal$tradingPlayer     引用   8 B（压缩指针 4 B）
      MerchantOffers  pal$offers            引用   8 B（压缩指针 4 B）
      long            pal$lastRestockDay          8 B
      ─────────────────────────────────────────────
      合计约 24 B/实例（开启压缩指针时约 16 B）

  典型服务器同时加载的 Mob 数量：数百 ~ 数千
      1000 只  ->  约 24 KB
      5000 只  ->  约 120 KB

  结论：完全可忽略。offers 采用懒加载（getOffers 首次调用才 new），
        非目标生物的 pal$offers 永远为 null，实际只多 2 个 null 引用 + 1 个 long。
""")

    print("=" * 78)
    print("决策建议")
    print("=" * 78)
    print(f"""
  方案 A（注入 Mob 基类）—— design 当前选择
      · 1 个 Mixin 类，代码量最小
      · 影响面：{len(concrete)} 个可实例化 Mob 子类（含 {len(extra)} 个非目标）
      · 内存：约 24 B x 实例数，可忽略
      · 兼容性：与其他改 Mob 的 Mod 有潜在冲突（R10）
      · 新增生物（含第三方 Mod）自动获得能力，靠运行时门控拦截

  方案 B（注入 38 个具体类）
      · 38 个 @Mixin target，或 1 个 Mixin 多 target 数组
      · 影响面精确为 38
      · 但：Brain 系 6 个与 Goal 系 32 个继承链不同，需分组
      · 且第三方 Mod 生物永远拿不到能力（与"已适配列表"模型一致）
      · 维护成本：每次 MC 版本更新需核对类名

  → 建议维持方案 A。理由：
      1. 内存开销可忽略（懒加载后每实例仅 2 null 引用 + 1 long）
      2. 运行时门控（已适配列表 ∩ 非白名单）已经能精确控制行为，
         "携带字段"与"启用行为"是两回事
      3. 方案 B 的 38 个 target 在 MC 版本更新时更易碎
""")


main()
