package top.windyvalley.peaceandlove.anger;

import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.item.PrimedTnt;
import net.minecraft.world.entity.player.Player;
import org.jetbrains.annotations.Nullable;

/**
 * 伤害源溯源判定器 —— T-ANGER-001，全项目语义最敏感的判定（用户两次强调的硬约束）。
 *
 * <p><b>核心规则</b>：只有「可归因到玩家」的伤害才触发仇恨，其余一律不介入。
 *
 * <p>判定链（对责任实体 {@code DamageSource#getEntity()} 溯源）：
 * <ol>
 *   <li>玩家本人（直接攻击 / 玩家投射物，投射物的 causingEntity 已解析为 owner）→ ✅</li>
 *   <li>宠物（{@link TamableAnimal} 且 owner 是玩家）→ ✅</li>
 *   <li>玩家点燃的 TNT（{@link PrimedTnt#getOwner()} 是玩家）→ ✅</li>
 *   <li>其余（铁傀儡 / 村民卫兵 / 怪物内斗 / 环境伤害）→ ❌ 走原版逻辑</li>
 * </ol>
 *
 * <p><b>投射物说明</b>（probe_damagesource.py 实测）：玩家射出的箭，
 * 其 {@code DamageSource.getEntity()} 返回射箭的玩家（owner 已解析），
 * 因此被第 1 条覆盖；{@code getDirectEntity()} 才是箭本身，本判定不用它。
 *
 * <p><b>可测性设计</b>：判定逻辑落在 {@link #attribute(EntityFeatures)} 这个
 * 纯函数上——输入是与 MC 解耦的 {@link EntityFeatures} 特征，输出归因。
 * 9 种伤害源在纯 JUnit 用特征组合覆盖；从 {@link Entity} 提取特征的
 * {@link #featuresOf(Entity)} 仅一行 instanceof，移交真机验证。
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
     * 纯逻辑判定：该特征的伤害源是否触发仇恨。
     *
     * <p>对应 9 种验收情况（✅ 触发 / ❌ 不介入）：
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
    public static boolean shouldTrigger(EntityFeatures f) {
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
     * 判定一个伤害源是否触发仇恨（真机入口）。
     *
     * @param source 伤害源（责任实体经 {@code getEntity()} 取，投射物已解析 owner）
     * @return 触发仇恨的玩家；不应触发时返回 {@code null}
     */
    @Nullable
    public static Player resolveAttackingPlayer(DamageSource source) {
        Entity attacker = source.getEntity();
        if (attacker instanceof Player player) {
            return player;
        }
        // 宠物 / TNT 溯源到玩家：取 owner 作为仇恨对象
        if (attacker instanceof TamableAnimal pet && pet.getOwner() instanceof Player owner) {
            return owner;
        }
        if (attacker instanceof PrimedTnt tnt && tnt.getOwner() instanceof Player owner) {
            return owner;
        }
        return null;
    }
}
