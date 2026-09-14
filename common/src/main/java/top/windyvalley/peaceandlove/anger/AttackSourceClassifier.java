package top.windyvalley.peaceandlove.anger;

import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.item.PrimedTnt;
import net.minecraft.world.entity.player.Player;
import org.jetbrains.annotations.Nullable;

/**
 * 伤害源溯源判定器 —— 只负责「是否归因到玩家」。
 *
 * <p>它不决定“能不能反击”，只决定“要不要做玩家专属的同族示警”。
 * 生物之间的正常受击反击仍由原版/Goal 机制处理。
 */
public final class AttackSourceClassifier {

    private AttackSourceClassifier() {
    }

    /**
     * 与 MC 解耦的伤害源特征 —— 判定所需的全部输入。
     *
     * @param isPlayer            责任实体是玩家本人
     * @param isPlayerOwnedPet    责任实体是宠物且其 owner 是玩家
     * @param isPlayerLitTnt      责任实体是 TNT 且其 owner 是玩家
     */
    public record EntityFeatures(boolean isPlayer,
                                 boolean isPlayerOwnedPet,
                                 boolean isPlayerLitTnt) {
    }

    /**
     * 纯逻辑判定：该特征的伤害源是否<b>归因到玩家</b>。
     *
     * <p>对应 9 种验收情况（✅ 玩家归因 / ❌ 非玩家归因）：
     * <pre>
     * 玩家直接攻击            (T,_,_) → ✅
     * 玩家投射物(箭/雪球/三叉戟) (T,_,_) → ✅   // getEntity 已解析为玩家
     * 玩家宠物(狼/猫)          (_,T,_) → ✅
     * 玩家点燃的 TNT/爆炸      (_,_,T) → ✅
     * 铁傀儡攻击              (F,F,F) → ❌
     * 村民卫兵攻击            (F,F,F) → ❌
     * 怪物内斗                (F,F,F) → ❌
     * 环境伤害(跌落/岩浆/窒息)  (F,F,F) → ❌
     * </pre>
     */
    public static boolean isPlayerAttribution(EntityFeatures f) {
        return f.isPlayer() || f.isPlayerOwnedPet() || f.isPlayerLitTnt();
    }

    /**
     * 从真实责任实体提取判定特征（一行 instanceof 链，真机验证）。
     */
    public static EntityFeatures featuresOf(@Nullable Entity attacker) {
        if (attacker == null) {
            return new EntityFeatures(false, false, false);
        }
        boolean isPlayer = attacker instanceof Player;
        boolean isPet = attacker instanceof TamableAnimal pet
                && pet.getOwner() instanceof Player;
        boolean isTnt = attacker instanceof PrimedTnt tnt
                && tnt.getOwner() instanceof Player;
        return new EntityFeatures(isPlayer, isPet, isTnt);
    }

    /**
     * 判定一个伤害源是否归因到玩家（真机入口）。
     *
     * @param source 伤害源（责任实体经 {@code getEntity()} 取，投射物已解析 owner）
     * @return 归因到玩家时返回该玩家；否则返回 {@code null}
     */
    @Nullable
    public static Player resolveAttackingPlayer(DamageSource source) {
        Entity attacker = source.getEntity();
        if (attacker instanceof Player player) {
            return player;
        }
        if (attacker instanceof TamableAnimal pet && pet.getOwner() instanceof Player owner) {
            return owner;
        }
        if (attacker instanceof PrimedTnt tnt && tnt.getOwner() instanceof Player owner) {
            return owner;
        }
        return null;
    }
}
