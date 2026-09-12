"""
R3 spike v3 —— 修正分类错误
================================

用户指出（2026-09-11）：
    「用户白名单和 Boss 天然跳过，工作量为零，这跟我的预期不一致。
      他们只是加入默认白名单，但管理员可以从白名单中移除，所以还是要适配的」

✅ 用户是对的。先前 v2 把「默认在白名单」等同于「不用实现」，这是分类错误。
   白名单是**运行时配置**，管理员移出后代码必须能正常工作。

本脚本重新为全部 39 个主动敌对生物（含先前判定为「零工作量」的 8 个）
判定 AI 系统类型，并评估各自的特殊适配难点。
"""

import io
import json
import re
import struct
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
JAR = BASE / "server-1.21.1.jar"
MAPPINGS = BASE / "server_mappings.txt"


def open_inner_jar(path):
    z = zipfile.ZipFile(path)
    inner = [n for n in z.namelist() if n.endswith(".jar") and "server" in n]
    if inner:
        with z.open(inner[0]) as f:
            return zipfile.ZipFile(io.BytesIO(f.read()))
    return z


def parse_mappings(path):
    """named class -> {obf, methods:{named:obf}, fields:{named:obf}}"""
    out, cur = {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            if not raw.startswith("    "):
                m = re.match(r"^(\S+) -> (\S+):$", raw.strip())
                if m:
                    cur = m.group(1)
                    out[cur] = {"obf": m.group(2), "methods": {}, "fields": {}}
            else:
                if cur is None:
                    continue
                s = raw.strip()
                mm = re.match(r"^(?:\d+:\d+:)?(\S+) (\S+)\((.*?)\) -> (\S+)$", s)
                if mm:
                    out[cur]["methods"].setdefault(mm.group(2), mm.group(4))
                    continue
                fm = re.match(r"^(\S+) (\S+) -> (\S+)$", s)
                if fm:
                    out[cur]["fields"].setdefault(fm.group(2), fm.group(3))
    return out


def parse_class(data):
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

    pos += 2                                    # access
    this_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    super_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    ic = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    ifaces = []
    for _ in range(ic):
        ifaces.append(cls_name(struct.unpack(">H", data[pos:pos + 2])[0])); pos += 2

    for _pass in range(2):                      # fields, then methods
        n = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        acc_list = []
        for _ in range(n):
            macc = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            mn = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
            md = cp.get(struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
            acc_list.append((mn, md, macc))
            ac = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            for _ in range(ac):
                pos += 2
                al = struct.unpack(">I", data[pos:pos + 4])[0]; pos += 4 + al
        if _pass == 0:
            fields = acc_list
        else:
            methods = acc_list

    return {"this": cls_name(this_i), "super": cls_name(super_i),
            "interfaces": ifaces, "fields": fields, "methods": methods}


# ── 全部 39 个主动敌对生物 ──
MOBS = {
    # (中文名, 类全名, 先前分组)
    "zombie":            ("僵尸", "net.minecraft.world.entity.monster.Zombie", "goal"),
    "zombie_villager":   ("僵尸村民", "net.minecraft.world.entity.monster.ZombieVillager", "goal"),
    "husk":              ("尸壳", "net.minecraft.world.entity.monster.Husk", "goal"),
    "drowned":           ("溺尸", "net.minecraft.world.entity.monster.Drowned", "goal"),
    "zombified_piglin":  ("僵尸猪灵", "net.minecraft.world.entity.monster.ZombifiedPiglin", "goal"),
    "skeleton":          ("骷髅", "net.minecraft.world.entity.monster.Skeleton", "goal"),
    "wither_skeleton":   ("凋灵骷髅", "net.minecraft.world.entity.monster.WitherSkeleton", "goal"),
    "stray":             ("流浪者", "net.minecraft.world.entity.monster.Stray", "goal"),
    "bogged":            ("沼骸", "net.minecraft.world.entity.monster.Bogged", "goal"),
    "giant":             ("巨人", "net.minecraft.world.entity.monster.Giant", "goal"),
    "spider":            ("蜘蛛", "net.minecraft.world.entity.monster.Spider", "goal"),
    "cave_spider":       ("洞穴蜘蛛", "net.minecraft.world.entity.monster.CaveSpider", "goal"),
    "creeper":           ("苦力怕", "net.minecraft.world.entity.monster.Creeper", "goal"),
    "ghast":             ("恶魂", "net.minecraft.world.entity.monster.Ghast", "goal"),
    "blaze":             ("烈焰人", "net.minecraft.world.entity.monster.Blaze", "goal"),
    "witch":             ("女巫", "net.minecraft.world.entity.monster.Witch", "goal"),
    "slime":             ("史莱姆", "net.minecraft.world.entity.monster.Slime", "goal"),
    "magma_cube":        ("岩浆怪", "net.minecraft.world.entity.monster.MagmaCube", "goal"),
    "enderman":          ("末影人", "net.minecraft.world.entity.monster.EnderMan", "goal"),
    "endermite":         ("末影螨", "net.minecraft.world.entity.monster.Endermite", "goal"),
    "guardian":          ("守卫者", "net.minecraft.world.entity.monster.Guardian", "goal"),
    "elder_guardian":    ("远古守卫者", "net.minecraft.world.entity.monster.ElderGuardian", "goal"),
    "illusioner":        ("幻术师", "net.minecraft.world.entity.monster.Illusioner", "goal"),
    "ravager":           ("劫掠兽", "net.minecraft.world.entity.monster.Ravager", "goal"),
    "silverfish":        ("蠹虫", "net.minecraft.world.entity.monster.Silverfish", "goal"),
    # Brain
    "piglin":            ("猪灵", "net.minecraft.world.entity.monster.piglin.Piglin", "brain"),
    "piglin_brute":      ("猪灵蛮兵", "net.minecraft.world.entity.monster.piglin.PiglinBrute", "brain"),
    "hoglin":            ("疣猪兽", "net.minecraft.world.entity.monster.hoglin.Hoglin", "brain"),
    "zoglin":            ("僵尸疣猪兽", "net.minecraft.world.entity.monster.Zoglin", "brain"),
    "warden":            ("监守者", "net.minecraft.world.entity.monster.warden.Warden", "brain"),
    "breeze":            ("旋风人", "net.minecraft.world.entity.monster.breeze.Breeze", "brain"),
    # 先前被判「零工作量」的 —— 本次重新判定
    "shulker":           ("潜影贝", "net.minecraft.world.entity.monster.Shulker", "whitelist"),
    "phantom":           ("幻翼", "net.minecraft.world.entity.monster.Phantom", "whitelist"),
    "pillager":          ("掠夺者", "net.minecraft.world.entity.monster.Pillager", "whitelist"),
    "vindicator":        ("卫道士", "net.minecraft.world.entity.monster.Vindicator", "whitelist"),
    "evoker":            ("唤魔者", "net.minecraft.world.entity.monster.Evoker", "whitelist"),
    "vex":               ("恼鬼", "net.minecraft.world.entity.monster.Vex", "whitelist"),
    "ender_dragon":      ("末影龙", "net.minecraft.world.entity.boss.enderdragon.EnderDragon", "boss"),
    "wither":            ("凋灵", "net.minecraft.world.entity.boss.wither.WitherBoss", "boss"),
}

BRAIN_MARKERS = ("makeBrain", "brainProvider")

# 各生物已知的特殊适配难点（基于 MC 机制，design 阶段需逐一验证）
NOTES = {
    "shulker":      "固定在方块上，攻击方式为发射导弹；无移动 Goal，索敌逻辑内嵌于 ShulkerAttackGoal",
    "phantom":      "飞行生物，用 PhantomAttackPlayerTargetGoal 而非标准 NearestAttackableTargetGoal；且有「玩家不睡觉才刷新」的生成条件",
    "pillager":     "属于袭击（Raid）系统，中立化会影响袭击事件；需处理 Raider.canJoinRaid",
    "vindicator":   "同属袭击系统；另有 Johnny 名牌特殊行为（攻击一切生物）",
    "evoker":       "同属袭击系统；召唤恼鬼 / 唤魔尖牙，中立后召唤物行为需一并处理",
    "vex":          "由唤魔者召唤，生命周期受召唤者控制；有 owner 概念，中立化需处理 owner 关系",
    "ender_dragon":  "Phase 系统（DragonPhaseInstance），无标准 targetSelector；且交易 UI 对 Boss 无意义",
    "wither":        "自有弹幕逻辑与 targetSelector，但 target 选择在 customServerAiStep 内硬编码",
}


def main():
    print("=" * 88)
    print("R3 v3 —— 修正分类：全部 39 个生物均需适配（白名单只是默认配置）")
    print("=" * 88)

    maps = parse_mappings(MAPPINGS)
    jar = open_inner_jar(JAR)

    results = []
    for mid, (zh, fqcn, prev_group) in MOBS.items():
        if fqcn not in maps:
            results.append((mid, zh, prev_group, "??", "mappings 中未找到", []))
            continue
        obf = maps[fqcn]["obf"]
        try:
            data = jar.read(obf.replace(".", "/") + ".class")
        except KeyError:
            results.append((mid, zh, prev_group, "??", "jar 中未找到类", []))
            continue

        info = parse_class(data)
        if info is None:
            results.append((mid, zh, prev_group, "??", "解析失败", []))
            continue

        # 判定：是否覆写 makeBrain / brainProvider
        m_obfs = set()
        for marker in BRAIN_MARKERS:
            o = maps[fqcn]["methods"].get(marker)
            if o:
                m_obfs.add(o)
        declared = {mn for mn, md, macc in info["methods"]}
        is_brain = bool(m_obfs & declared)

        # 也检查父类（如 PiglinBrute 继承 AbstractPiglin）
        parent_brain = False
        sup = info["super"]
        if sup:
            sup_named = None
            for k, v in maps.items():
                if v["obf"].replace(".", "/") == sup:
                    sup_named = k
                    break
            if sup_named and sup_named in maps:
                sup_obf = maps[sup_named]["obf"]
                try:
                    sdata = jar.read(sup_obf.replace(".", "/") + ".class")
                    sinfo = parse_class(sdata)
                    if sinfo:
                        sdecl = {mn for mn, md, macc in sinfo["methods"]}
                        smk = set()
                        for marker in BRAIN_MARKERS:
                            o = maps[sup_named]["methods"].get(marker)
                            if o:
                                smk.add(o)
                        parent_brain = bool(smk & sdecl)
                except KeyError:
                    pass

        system = "Brain" if (is_brain or parent_brain) else "Goal"
        results.append((mid, zh, prev_group, system, "", NOTES.get(mid, "")))

    # ── 输出 ──
    print("\n【1】全部 39 个生物的 AI 系统判定\n")
    print("  %-20s %-12s %-10s %-8s %s" % ("ID", "名称", "先前分组", "AI系统", "特殊难点"))
    print("  " + "-" * 100)
    for mid, zh, prev, system, err, note in results:
        flag = ""
        if prev in ("whitelist", "boss"):
            flag = " ★"
        n = (note[:44] + "…") if len(note) > 45 else note
        print("  %-20s %-12s %-10s %-8s%s %s" % (mid, zh, prev, system, flag, n))

    # ── 重新分组 ──
    print("\n" + "=" * 88)
    print("【2】修正后的实现分组（按 AI 系统，而非按是否在白名单）")
    print("=" * 88)

    goal_all = [r for r in results if r[3] == "Goal"]
    brain_all = [r for r in results if r[3] == "Brain"]

    print(f"\n  Goal 系统：{len(goal_all)} 个")
    for mid, zh, prev, system, err, note in goal_all:
        tag = {"goal": "", "whitelist": "  ← 先前误判为零工作量",
               "boss": "  ← 先前误判为零工作量"}.get(prev, "")
        print(f"     {zh:12}{tag}")

    print(f"\n  Brain 系统：{len(brain_all)} 个")
    for mid, zh, prev, system, err, note in brain_all:
        tag = {"goal": "", "whitelist": "  ← 先前误判为零工作量",
               "boss": "  ← 先前误判为零工作量"}.get(prev, "")
        print(f"     {zh:12}{tag}")

    # ── 需要额外特殊处理的 ──
    print("\n" + "=" * 88)
    print("【3】需要额外特殊适配的生物（超出标准 Goal/Brain 改写）")
    print("=" * 88)
    print()
    for mid, zh, prev, system, err, note in results:
        if note:
            print(f"  ▸ {zh}（{system}）")
            print(f"      {note}\n")

    # ── 工作量重估 ──
    print("=" * 88)
    print("【4】工作量重估")
    print("=" * 88)
    special = sum(1 for r in results if r[5])
    print(f"""
  先前 v2 的错误分组：
      Goal 25 + Brain 6 + 白名单 6（零工作量）+ Boss 2（零工作量）
      → 实际要实现 31 个

  修正后：
      Goal {len(goal_all)} 个 + Brain {len(brain_all)} 个 = {len(results)} 个全部要实现
      其中 {special} 个需要超出标准改写的特殊适配

  ⚠️ 工作量增加，但增量小于「+8 个生物」的直觉估计：
     - 袭击系 3 个（掠夺者/卫道士/唤魔者）共享 Raider 基类，可一并处理
     - 恼鬼依附唤魔者，处理完唤魔者后成本很低
     - 真正独立的是：潜影贝、幻翼、末影龙、凋灵 4 个

  📌 Boss 的特殊性仍然成立，但结论要改写：
     不是「不用做」，而是「做出来后交易 UI 对 Boss 意义不大」。
     建议：仍实现中立化逻辑（管理员移出白名单时能生效），
           但对 Boss **不生成交易 offer**，或提供独立开关。
""")

    # 落盘
    out = {
        "mc_version": "1.21.1",
        "correction": "白名单与 Boss 并非零工作量；白名单是运行时配置，移出后代码必须能工作",
        "goal_system": [{"id": r[0], "zh": r[1], "default_whitelisted": r[2] in ("whitelist", "boss")}
                        for r in goal_all],
        "brain_system": [{"id": r[0], "zh": r[1], "default_whitelisted": r[2] in ("whitelist", "boss")}
                         for r in brain_all],
        "special_adaptations": {r[0]: r[5] for r in results if r[5]},
    }
    p = BASE / "neutralization_plan_v3.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ 已写入 {p.name}")


if __name__ == "__main__":
    main()
