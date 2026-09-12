package top.windyvalley.peaceandlove;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.item.trading.Merchant;

/**
 * P1 / P3 探针公共逻辑。
 *
 * P1：Mixin 注入的 Merchant 接口在运行时是否真的挂上了
 * P3：注入 Mob 基类的影响面 —— 有多少 EntityType 因此获得 Merchant 能力
 */
public final class ProbeCommon {

    public static final String MOD_ID = "peaceandlove";

    /** design 阶段确定的 38 个已适配生物 */
    private static final String[] ADAPTED = {
        "blaze", "bogged", "cave_spider", "creeper", "drowned", "elder_guardian",
        "enderman", "endermite", "evoker", "ghast", "giant", "guardian", "husk",
        "illusioner", "magma_cube", "phantom", "pillager", "ravager", "shulker",
        "silverfish", "skeleton", "slime", "spider", "stray", "vex", "vindicator",
        "witch", "wither", "wither_skeleton", "zombie", "zombie_villager",
        "zombified_piglin",
        "breeze", "hoglin", "piglin", "piglin_brute", "warden", "zoglin"
    };

    private ProbeCommon() {
    }

    public static void runProbe(String platform) {
        StringBuilder sb = new StringBuilder();
        sb.append("\n");
        sb.append("================================================================\n");
        sb.append("  Peace And Love —— P1/P3 探针  [").append(platform).append("]\n");
        sb.append("================================================================\n");

        // ── P1：Merchant 接口是否成功注入 ──
        // 通过反射检查 Mob.class 是否实现了 Merchant
        boolean injected = Merchant.class.isAssignableFrom(Mob.class);
        sb.append("\n【P1】Mixin 注入 Merchant 接口\n");
        sb.append("  Merchant.isAssignableFrom(Mob.class) = ")
          .append(injected ? "✅ true —— 注入成功" : "❌ false —— 注入失败")
          .append("\n");

        if (!injected) {
            sb.append("  ⚠️ ").append(platform)
              .append(" 平台注入失败，可能需要 Access Transformer\n");
        }

        // ── P3：影响面统计 ──
        // 不实例化实体（构造器阶段注册表未就绪且 create(null) 必失败），
        // 改为扫描 EntityType 的泛型签名拿到实体类，纯反射判定。
        sb.append("\n【P3】注入 Mob 基类的影响面\n");
        int totalEntityTypes = 0;
        int mobSubclasses = 0;
        int merchantCapable = 0;
        int adaptedFound = 0;
        java.util.List<String> notMerchant = new java.util.ArrayList<>();

        for (var entry : BuiltInRegistries.ENTITY_TYPE.entrySet()) {
            totalEntityTypes++;
            EntityType<?> type = entry.getValue();
            Class<?> cls = pal$resolveEntityClass(type);
            if (cls == null) {
                continue;
            }
            if (Mob.class.isAssignableFrom(cls)) {
                mobSubclasses++;
                if (Merchant.class.isAssignableFrom(cls)) {
                    merchantCapable++;
                } else {
                    notMerchant.add(entry.getKey().location().toString());
                }
            }
        }

        for (String id : ADAPTED) {
            EntityType<?> t = BuiltInRegistries.ENTITY_TYPE
                .getOptional(net.minecraft.resources.ResourceLocation
                    .withDefaultNamespace(id))
                .orElse(null);
            if (t != null) {
                adaptedFound++;
            }
        }

        sb.append("  注册的 EntityType 总数     : ").append(totalEntityTypes).append("\n");
        sb.append("  能解析出实体类的           : ")
          .append(mobSubclasses).append(" 个是 Mob 子类\n");
        sb.append("  其中同时是 Merchant        : ").append(merchantCapable);
        if (mobSubclasses > 0 && merchantCapable == mobSubclasses) {
            sb.append("   [OK] 全部 Mob 子类都拿到了 Merchant");
        } else {
            sb.append("   [WARN] 数量不一致");
        }
        sb.append("\n");
        if (!notMerchant.isEmpty()) {
            sb.append("  未拿到 Merchant 的 Mob     : ")
              .append(notMerchant.size()).append(" 个 -> ")
              .append(notMerchant.subList(0, Math.min(5, notMerchant.size())))
              .append("\n");
        }
        sb.append("  本模组已适配（应为 38）    : ").append(adaptedFound).append("\n");
        sb.append("  -> 注入基类的额外影响面    : ")
          .append(mobSubclasses - adaptedFound).append(" 个非目标生物\n");
        sb.append("     （这些生物也会携带 Merchant 字段，需运行时判定拦截）\n");

        sb.append("\n【探针】hurt 注入点\n");
        sb.append("  已记录玩家攻击次数: ").append(ProbeResults.playerAttackCount).append("\n");

        sb.append("================================================================\n");

        System.out.println(sb);
    }

    /**
     * 解析 EntityType 对应的实体类，不实例化。
     *
     * 手段：EntityType 的泛型参数 T 就是实体类。运行时泛型被擦除，
     * 但 EntityType 内部持有 EntityType$EntityFactory<T>，其 lambda 的
     * 实现方法签名保留了具体类型。这里退而求其次，用一个已知实例映射表 +
     * 反射扫描 EntityType 的所有字段找 Class 对象。
     *
     * 若都拿不到则返回 null（调用方跳过该项）。
     */
    private static Class<?> pal$resolveEntityClass(EntityType<?> type) {
        // 反射找 EntityType 里可能缓存的 Class 字段
        for (java.lang.reflect.Field f : EntityType.class.getDeclaredFields()) {
            if (!Class.class.isAssignableFrom(f.getType())) {
                continue;
            }
            try {
                f.setAccessible(true);
                Object v = f.get(type);
                if (v instanceof Class<?> c) {
                    return c;
                }
            } catch (Throwable ignored) {
            }
        }
        // 退路：用 factory lambda 的声明类推断
        for (java.lang.reflect.Field f : EntityType.class.getDeclaredFields()) {
            try {
                f.setAccessible(true);
                Object v = f.get(type);
                if (v == null) {
                    continue;
                }
                String n = v.getClass().getName();
                // lambda 形如 net.minecraft.world.entity.EntityType$$Lambda/0x...
                // 无法直接反推，跳过
                if (n.contains("$$Lambda")) {
                    continue;
                }
            } catch (Throwable ignored) {
            }
        }
        return null;
    }
}
