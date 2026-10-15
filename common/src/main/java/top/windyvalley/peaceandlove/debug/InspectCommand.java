package top.windyvalley.peaceandlove.debug;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import dev.architectury.event.events.common.CommandRegistrationEvent;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import top.windyvalley.peaceandlove.PeaceAndLove;

import java.util.List;

/**
 * {@code /pal inspect} 只读诊断命令。
 *
 * <p>玩家注视 32 格内的生物时，回显该生物的<b>门控链</b>（适配/白名单/
 * 中立化/可交易）与<b>仇恨链</b>（是否愤怒/来源/剩余时间/当前目标距离）。
 * 排查「为什么这只怪还在追 / 为什么不能交易 / 白名单有没有生效」时，
 * 不必再连自动化客户端跑 verify RPC。
 *
 * <p>命令层只做选取与回显：字段采集在 {@link MobInspector}，文案渲染在
 * {@link MobInspection#toLines()}。注册与选取依赖服务端运行时，真机验证；
 * 渲染结论已由 {@code MobInspectionTest} 纯 JUnit 覆盖。
 *
 * <p>主命令 {@code /pal} 由 {@code ConfigCommand} 建立，这里向同名根追加
 * {@code inspect} 子节点（Brigadier 对同名 literal 做子树合并），并对
 * {@code /peaceandlove} 别名同样追加。权限 OP level 2。
 */
public final class InspectCommand {

    /** 权限等级：OP 2（与 ConfigCommand 一致）。 */
    private static final int PERM_OP = 2;

    /** 注视选取距离（格），与玩家常规交互距离相比放宽到 32，便于观察。 */
    private static final double REACH = 32.0;

    public void register() {
        CommandRegistrationEvent.EVENT.register((dispatcher, registry, selection) -> {
            for (String root : new String[]{"pal", "peaceandlove"}) {
                dispatcher.register(buildRoot(root));
            }
        });
    }

    private LiteralArgumentBuilder<CommandSourceStack> buildRoot(String name) {
        return Commands.literal(name)
                .requires(src -> src.hasPermission(PERM_OP))
                .then(Commands.literal("inspect").executes(this::inspect));
    }

    private int inspect(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack src = ctx.getSource();
        Player player = src.getPlayer();
        if (player == null) {
            src.sendFailure(Component.literal("[PAL] /pal inspect 只能由玩家执行"));
            return 0;
        }

        Mob mob = pickMob(player);
        if (mob == null) {
            src.sendFailure(Component.literal(
                    "§e[PAL] §7准星 " + (long) REACH + " 格内没有可检查的生物"));
            return 0;
        }

        MobInspection info = MobInspector.inspect(mob, PeaceAndLove.config().get());
        List<String> lines = info.toLines();
        for (String line : lines) {
            src.sendSuccess(() -> Component.literal(line), false);
        }
        return 1;
    }

    /**
     * 沿玩家视线选取生物。与攻击命中同款 {@link ProjectileUtil#getEntityHitResult}，
     * 谓词经 {@link MobInspector#asMob} 同时接受末影龙多部分碰撞体。
     */
    private Mob pickMob(Player player) {
        Vec3 eye = player.getEyePosition(1.0F);
        Vec3 view = player.getViewVector(1.0F);
        Vec3 end = eye.add(view.scale(REACH));
        AABB searchBox = player.getBoundingBox()
                .expandTowards(view.scale(REACH))
                .inflate(1.0);
        EntityHitResult hit = ProjectileUtil.getEntityHitResult(
                player, eye, end, searchBox,
                e -> MobInspector.asMob(e) != null && e.isPickable(),
                eye.distanceToSqr(end));
        if (hit == null) {
            return null;
        }
        return MobInspector.asMob(hit.getEntity());
    }
}
