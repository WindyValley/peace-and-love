package top.windyvalley.peaceandlove.config;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import dev.architectury.event.events.common.CommandRegistrationEvent;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.Component;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.AdaptedMobs;

import java.util.List;

/**
 * {@code /pal} 命令族。
 *
 * <p>命令层<b>只做参数解析和消息回显</b>，所有逻辑委托给已单测覆盖的
 * {@link ConfigManager} —— 不在命令层重写业务逻辑。
 *
 * <p>子命令：
 * <ul>
 *   <li>{@code /pal reload} —— 热重载配置</li>
 *   <li>{@code /pal whitelist list} —— 列出白名单</li>
 *   <li>{@code /pal whitelist add <id>} —— 加入白名单（tab 补全来自已适配列表）</li>
 *   <li>{@code /pal whitelist remove <id>} —— 移出白名单</li>
 * </ul>
 *
 * <p>主命令 {@code /pal} 与别名 {@code /peaceandlove} 同时注册。
 * 权限要求 OP level 2。
 *
 * <p><b>⚠️ 验证方式说明</b>：命令注册、权限、tab 补全依赖服务端运行时
 * （Brigadier + MC 命令调度），无法用纯 JUnit 验证。本类标注为
 * 「已写未验」，待 T-NEUT 挂上 Mixin、服务端可启动后连同门控实际效果
 * 一并真机验证。
 */
public final class ConfigCommand {

    /** 权限等级：OP 2。 */
    private static final int PERM_OP = 2;

    private final ConfigManager manager;

    public ConfigCommand(ConfigManager manager) {
        this.manager = manager;
    }

    /** 注册到 Architectury 命令事件。 */
    public void register() {
        CommandRegistrationEvent.EVENT.register((dispatcher, registry, selection) -> {
            registerRoot(dispatcher, "pal");
            registerRoot(dispatcher, "peaceandlove");
        });
    }

    private void registerRoot(com.mojang.brigadier.CommandDispatcher<CommandSourceStack> dispatcher,
                              String name) {
        dispatcher.register(
                Commands.literal(name)
                        .requires(src -> src.hasPermission(PERM_OP))
                        .then(reloadNode())
                        .then(whitelistNode())
        );
    }

    // ─────────────────────────── reload ───────────────────────────

    private LiteralArgumentBuilder<CommandSourceStack> reloadNode() {
        return Commands.literal("reload")
                .executes(this::reload);
    }

    private int reload(CommandContext<CommandSourceStack> ctx) {
        ConfigManager.ReloadResult result = manager.reload();
        CommandSourceStack src = ctx.getSource();
        if (result.success()) {
            src.sendSuccess(() -> Component.literal("[Peace And Love] " + result.message()), true);
            PeaceAndLove.LOGGER.info("配置已重载（by {}）：{}", src.getTextName(), result.message());
            return 1;
        }
        src.sendFailure(Component.literal("[Peace And Love] " + result.message()));
        return 0;
    }

    // ─────────────────────────── whitelist ───────────────────────────

    private LiteralArgumentBuilder<CommandSourceStack> whitelistNode() {
        return Commands.literal("whitelist")
                .then(Commands.literal("list").executes(this::whitelistList))
                .then(Commands.literal("add")
                        .then(Commands.argument("id", StringArgumentType.word())
                                .suggests(adaptedSuggestions())
                                .executes(ctx -> whitelistChange(ctx, true))))
                .then(Commands.literal("remove")
                        .then(Commands.argument("id", StringArgumentType.word())
                                .suggests(whitelistSuggestions())
                                .executes(ctx -> whitelistChange(ctx, false))));
    }

    private int whitelistList(CommandContext<CommandSourceStack> ctx) {
        List<String> wl = manager.get().hostile_whitelist();
        CommandSourceStack src = ctx.getSource();
        if (wl.isEmpty()) {
            src.sendSuccess(() -> Component.literal("[Peace And Love] 白名单为空"), false);
            return 0;
        }
        src.sendSuccess(() -> Component.literal(
                "[Peace And Love] 白名单（" + wl.size() + " 项）："), false);
        for (String id : wl) {
            String note = top.windyvalley.peaceandlove.scope.NeutralizationScope
                    .isIneffectiveWhitelistEntry(id) ? " §7（未适配，无效）§r" : "";
            src.sendSuccess(() -> Component.literal("  - " + id + note), false);
        }
        return wl.size();
    }

    private int whitelistChange(CommandContext<CommandSourceStack> ctx, boolean add) {
        String id = StringArgumentType.getString(ctx, "id");
        ConfigManager.WhitelistChange change = manager.changeWhitelist(id, add);
        CommandSourceStack src = ctx.getSource();
        if (change.changed()) {
            src.sendSuccess(() -> Component.literal("[Peace And Love] " + change.message()), true);
            PeaceAndLove.LOGGER.info("白名单变更（by {}）：{}", src.getTextName(), change.message());
            return 1;
        }
        src.sendSuccess(() -> Component.literal("[Peace And Love] " + change.message()), false);
        return 0;
    }

    // ─────────────────────────── 补全 ───────────────────────────

    /** add 的候选来自已适配列表（避免输入无效 id），去掉已在白名单中的。 */
    private SuggestionProvider<CommandSourceStack> adaptedSuggestions() {
        return (ctx, builder) -> {
            List<String> current = manager.get().hostile_whitelist();
            List<String> candidates = AdaptedMobs.adaptedIds().stream()
                    .filter(id -> !current.contains(id))
                    .sorted()
                    .toList();
            return SharedSuggestionProvider.suggest(candidates, builder);
        };
    }

    /** remove 的候选来自当前白名单。 */
    private SuggestionProvider<CommandSourceStack> whitelistSuggestions() {
        return (ctx, builder) -> SharedSuggestionProvider.suggest(
                manager.get().hostile_whitelist().stream().sorted().toList(), builder);
    }
}
