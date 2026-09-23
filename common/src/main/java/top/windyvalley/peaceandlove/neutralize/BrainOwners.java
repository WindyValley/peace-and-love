package top.windyvalley.peaceandlove.neutralize;

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.Brain;

import java.lang.ref.WeakReference;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Brain → 拥有者实体 的登记处。
 *
 * <p>{@link Brain} 对象自身<b>不持有实体引用</b>（字节码核实字段中无 owner），
 * 而拦截 {@code setMemoryInternal} 时必须知道「这是谁的脑子」才能做门控。
 * 这里用 Brain 实例做键登记它的主人：
 * <ul>
 *   <li>实体加入世界时由中立化服务登记一次（覆盖第一次 tick 前的窗口）；</li>
 *   <li>每次 {@code Brain.tick} HEAD 再次登记（兜底）。</li>
 * </ul>
 *
 * <p>键值均为弱引用：键随 Brain 被回收、值随实体被回收后，
 * {@link #prune()} 清理死条目，避免长期运行堆积。
 */
public final class BrainOwners {

    private static final ConcurrentHashMap<IdentityKey, WeakReference<LivingEntity>> OWNERS =
            new ConcurrentHashMap<>();

    private BrainOwners() {
    }

    /** 登记（或更新）一个 Brain 的主人。brain/owner 为 null 时忽略。 */
    public static void set(Brain<?> brain, LivingEntity owner) {
        if (brain == null || owner == null) {
            return;
        }
        OWNERS.put(new IdentityKey(brain), new WeakReference<>(owner));
    }

    /** 取一个 Brain 登记的主人；未登记或已被回收时返回 null。 */
    public static LivingEntity get(Brain<?> brain) {
        if (brain == null) {
            return null;
        }
        WeakReference<LivingEntity> ref = OWNERS.get(new IdentityKey(brain));
        return ref == null ? null : ref.get();
    }

    /** 清理键/值已被回收的死条目。 */
    public static void prune() {
        OWNERS.entrySet().removeIf(e -> e.getKey().isDead() || e.getValue().get() == null);
    }

    static int size() {
        return OWNERS.size();
    }

    /** 以身份相等（==）比较的 Brain 键；弱引用随 Brain 一起回收。 */
    private static final class IdentityKey {
        private final WeakReference<Brain<?>> ref;

        IdentityKey(Brain<?> brain) {
            this.ref = new WeakReference<>(brain);
        }

        Brain<?> brain() {
            return ref.get();
        }

        boolean isDead() {
            return ref.get() == null;
        }

        @Override
        public boolean equals(Object o) {
            if (!(o instanceof IdentityKey other)) {
                return false;
            }
            return this.ref.get() != null && this.ref.get() == other.ref.get();
        }

        @Override
        public int hashCode() {
            Brain<?> b = ref.get();
            return System.identityHashCode(b);
        }
    }
}
