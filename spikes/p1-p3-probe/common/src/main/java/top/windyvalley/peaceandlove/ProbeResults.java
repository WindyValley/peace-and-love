package top.windyvalley.peaceandlove;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;

/**
 * 探针结果收集器。
 *
 * ★ 必须放在 mixin 包**之外** —— Mixin 规定 mixin 包内的类不能被普通代码
 *   直接引用，否则抛 IllegalClassLoadError:
 *   "... is in a defined mixin package ... and cannot be referenced directly"
 */
public final class ProbeResults {

    public static volatile int playerAttackCount = 0;
    public static volatile String lastAttack = "(none)";

    private ProbeResults() {
    }

    public static void recordPlayerAttack(Mob mob, Player player) {
        playerAttackCount++;
        lastAttack = mob.getType().toString() + " <- " + player.getName().getString();
    }
}
