"""
design 阶段接口核实 —— 从 1.21.1 字节码提取真实签名
======================================================
目的：02-design.md 里写的每个接口签名、方法名、字段名都必须来自实测，
      不能凭印象写。本脚本提取 design 需要引用的全部符号。

覆盖：
  1. Merchant 接口的完整方法签名（方案 A 要实现的 11 个方法）
  2. Mob.hurt / LivingEntity.hurt 的签名（仇恨触发点）
  3. DamageSource 取攻击者的方法（判定「是否玩家攻击」）
  4. NeutralMob 接口方法（复用原版记仇机制）
  5. Goal / GoalSelector 的关键方法（移除索敌 Goal）
  6. Brain / Behavior 关键方法
  7. MerchantOffer 构造器与 MerchantOffers
  8. LootTable / LootPool 可访问性（R1 已验证，这里取精确签名）
"""
import io
import re
import struct
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
JAR = BASE.parent / "r3-ai" / "server-1.21.1.jar"
MAPPINGS = BASE.parent / "r3-ai" / "server_mappings.txt"


def open_mc_jar(path):
    """1.21.1 server.jar 是 bundler 壳，真代码在 META-INF/versions/ 内层。"""
    outer = zipfile.ZipFile(path)
    inner_name = None
    for n in outer.namelist():
        if n.startswith("META-INF/versions/") and n.endswith(".jar"):
            inner_name = n
            break
    if inner_name is None:
        return outer
    data = outer.read(inner_name)
    return zipfile.ZipFile(io.BytesIO(data))


def load_mappings():
    """proguard mappings: 官方名 -> 混淆名"""
    n2o, o2n = {}, {}
    members = {}
    cur = None
    with open(MAPPINGS, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            if not line.startswith("    "):
                m = re.match(r"^(\S+) -> (\S+):", line)
                if m:
                    cur = m.group(1)
                    n2o[cur] = m.group(2)
                    o2n[m.group(2)] = cur
                    members[cur] = {"fields": {}, "methods": {}}
            elif cur:
                s = line.strip()
                m = re.match(r"^(?:\d+:\d+:)?(\S+) (\S+)\((.*?)\) -> (\S+)$", s)
                if m:
                    members[cur]["methods"].setdefault(m.group(4), []).append(
                        (m.group(2), m.group(1), m.group(3))
                    )
                    continue
                m = re.match(r"^(\S+) (\S+) -> (\S+)$", s)
                if m:
                    members[cur]["fields"][m.group(3)] = (m.group(2), m.group(1))
    return n2o, o2n, members


CP_TAGS = {
    7: ("class", 2), 9: ("fieldref", 4), 10: ("methodref", 4),
    11: ("ifaceref", 4), 8: ("string", 2), 3: ("int", 4), 4: ("float", 4),
    5: ("long", 8), 6: ("double", 8), 12: ("nameandtype", 4),
    15: ("methodhandle", 3), 16: ("methodtype", 2), 17: ("dynamic", 4),
    18: ("invokedynamic", 4), 19: ("module", 2), 20: ("package", 2),
}


def parse_class(data):
    if data[:4] != b"\xca\xfe\xba\xbe":
        return None
    off = 8
    cp_count = struct.unpack(">H", data[off:off + 2])[0]
    off += 2
    cp = {}
    i = 1
    while i < cp_count:
        tag = data[off]
        off += 1
        if tag == 1:
            ln = struct.unpack(">H", data[off:off + 2])[0]
            off += 2
            cp[i] = ("utf8", data[off:off + ln].decode("utf-8", "replace"))
            off += ln
        else:
            name, size = CP_TAGS.get(tag, (None, None))
            if size is None:
                return None
            cp[i] = (name, data[off:off + size])
            off += size
            if tag in (5, 6):
                i += 1
        i += 1

    def utf8(idx):
        e = cp.get(idx)
        return e[1] if e and e[0] == "utf8" else None

    def cls_name(idx):
        e = cp.get(idx)
        if not e or e[0] != "class":
            return None
        return utf8(struct.unpack(">H", e[1])[0])

    off += 2  # access
    this_i = struct.unpack(">H", data[off:off + 2])[0]; off += 2
    super_i = struct.unpack(">H", data[off:off + 2])[0]; off += 2
    this_name = cls_name(this_i)
    super_name = cls_name(super_i) if super_i else None

    ifc_count = struct.unpack(">H", data[off:off + 2])[0]; off += 2
    ifaces = []
    for _ in range(ifc_count):
        ifaces.append(cls_name(struct.unpack(">H", data[off:off + 2])[0]))
        off += 2

    def skip_attrs(o):
        n = struct.unpack(">H", data[o:o + 2])[0]; o += 2
        for _ in range(n):
            o += 2
            ln = struct.unpack(">I", data[o:o + 4])[0]; o += 4
            o += ln
        return o

    fields = []
    fcount = struct.unpack(">H", data[off:off + 2])[0]; off += 2
    for _ in range(fcount):
        acc = struct.unpack(">H", data[off:off + 2])[0]; off += 2
        nm = utf8(struct.unpack(">H", data[off:off + 2])[0]); off += 2
        de = utf8(struct.unpack(">H", data[off:off + 2])[0]); off += 2
        off = skip_attrs(off)
        fields.append((nm, de, acc))

    methods = []
    mcount = struct.unpack(">H", data[off:off + 2])[0]; off += 2
    for _ in range(mcount):
        acc = struct.unpack(">H", data[off:off + 2])[0]; off += 2
        nm = utf8(struct.unpack(">H", data[off:off + 2])[0]); off += 2
        de = utf8(struct.unpack(">H", data[off:off + 2])[0]); off += 2
        off = skip_attrs(off)
        methods.append((nm, de, acc & 0x0400 != 0, acc))

    return {"this": this_name, "super": super_name, "ifaces": ifaces,
            "fields": fields, "methods": methods}


ACC = [(0x0001, "public"), (0x0002, "private"), (0x0004, "protected"),
       (0x0008, "static"), (0x0010, "final"), (0x0400, "abstract")]


def acc_str(a):
    return " ".join(n for b, n in ACC if a & b)


def main():
    n2o, o2n, members = load_mappings()
    zf = open_mc_jar(JAR)
    names = set(zf.namelist())

    def show(fq, title, want_methods=None, want_fields=None):
        print(f"\n{'=' * 74}\n{title}\n  {fq}\n{'=' * 74}")
        obf = n2o.get(fq)
        if not obf:
            print("  ❌ mappings 中找不到")
            return
        entry = f"{obf.replace('.', '/')}.class"
        if entry not in names:
            print(f"  ❌ jar 中找不到 {entry}")
            return
        info = parse_class(zf.read(entry))
        if not info:
            print("  ❌ 解析失败")
            return
        mem = members.get(fq, {"fields": {}, "methods": {}})

        # 接口
        if info["ifaces"]:
            ifn = [o2n.get(x.replace("/", "."), x) for x in info["ifaces"]]
            print(f"  implements: {', '.join(ifn)}")
        if info["super"]:
            sup = o2n.get(info["super"].replace("/", "."), info["super"])
            print(f"  extends   : {sup}")

        if want_fields is not None:
            print("\n  -- 字段 --")
            for fname, fdesc, facc in info["fields"]:
                real = mem["fields"].get(fname)
                rn = real[1] if real else fname
                rt = real[0] if real else fdesc
                if want_fields and not any(w in rn for w in want_fields):
                    continue
                print(f"    {acc_str(facc):24} {rt:42} {rn}")

        if want_methods is not None:
            print("\n  -- 方法 --")
            seen = set()
            for mname, mdesc, mabs, macc in info["methods"]:
                cands = mem["methods"].get(mname, [])
                rn = cands[0][0] if cands else mname
                rt = cands[0][1] if cands else "?"
                rp = cands[0][2] if cands else "?"
                if want_methods and not any(w in rn for w in want_methods):
                    continue
                key = (rn, rp)
                if key in seen:
                    continue
                seen.add(key)
                flag = " [abstract]" if mabs else ""
                print(f"    {acc_str(macc):20} {rt:34} {rn}({rp}){flag}")

    print("=" * 74)
    print("design 阶段接口核实 —— 全部签名来自 1.21.1 官方 jar + mappings")
    print("=" * 74)

    show("net.minecraft.world.item.trading.Merchant",
         "① Merchant 接口 —— 方案 A 需实现的全部方法", want_methods=[])

    show("net.minecraft.world.entity.npc.InventoryCarrier",
         "①b InventoryCarrier（若 Merchant 需要）", want_methods=[])

    show("net.minecraft.world.entity.Mob",
         "② Mob —— 中立化注入点",
         want_methods=["hurt", "setTarget", "getTarget", "goalSelector",
                       "registerGoals", "mobInteract", "addAdditionalSaveData",
                       "readAdditionalSaveData"],
         want_fields=["goalSelector", "targetSelector", "target"])

    show("net.minecraft.world.entity.LivingEntity",
         "③ LivingEntity.hurt —— 伤害入口",
         want_methods=["hurt", "getLastHurtByMob", "setLastHurtByMob",
                       "getLastHurtByPlayer"])

    show("net.minecraft.world.damagesource.DamageSource",
         "④ DamageSource —— 判定「是否玩家攻击」的关键",
         want_methods=[])

    show("net.minecraft.world.entity.NeutralMob",
         "⑤ NeutralMob —— 复用原版记仇/冷却机制", want_methods=[])

    show("net.minecraft.world.entity.ai.goal.GoalSelector",
         "⑥ GoalSelector —— 移除索敌 Goal 的操作接口", want_methods=[])

    show("net.minecraft.world.item.trading.MerchantOffer",
         "⑦ MerchantOffer —— 交易与补货",
         want_methods=["Uses", "OutOfStock", "getResult", "getCostA",
                       "getBaseCostA", "getCostB", "assemble", "satisfiedBy"],
         want_fields=[])

    show("net.minecraft.world.item.trading.MerchantOffers",
         "⑧ MerchantOffers", want_methods=[])

    show("net.minecraft.world.entity.ai.Brain",
         "⑨ Brain —— Brain 系生物的改写接口",
         want_methods=["removeAllBehaviors", "addActivity", "setMemory",
                       "eraseMemory", "getMemory", "setActiveActivity",
                       "useDefaultActivity"])

    print("\n" + "=" * 74)
    print("完成")
    print("=" * 74)


if __name__ == "__main__":
    main()
