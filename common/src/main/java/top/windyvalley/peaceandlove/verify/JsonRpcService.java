package top.windyvalley.peaceandlove.verify;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.anger.AngerController;
import top.windyvalley.peaceandlove.trade.RestockManager;

import java.io.*;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * JSON-RPC TCP 服务 —— 用于真机验证时远程操控玩家。
 *
 * <p>监听 25585 端口（可配置），接收 JSON-RPC 2.0 请求：
 * <pre>
 * {"jsonrpc":"2.0","method":"player.attack","params":{"target":"zombie"},"id":1}
 * </pre>
 *
 * <p>方法清单：
 * <ul>
 *   <li>{@code player.attack} —— 玩家攻击最近的指定生物</li>
 *   <li>{@code player.move} —— 玩家向指定方向移动</li>
 *   <li>{@code player.pos} —— 查询玩家位置</li>
 *   <li>{@code entity.list} —— 列出周围生物</li>
 *   <li>{@code server.status} —— 服务器状态</li>
 * </ul>
 *
 * <p>只在服务端启动时开启，生产环境应通过配置关闭。
 */
public final class JsonRpcService {

    /** 默认验证探针端口；同机多服用 -Dpal.verifyRpcPort 覆盖。 */
    public static final int DEFAULT_PORT = 25585;
    private static final Gson GSON = new Gson();

    private final MinecraftServer server;
    private final int port;
    private ServerSocket serverSocket;
    private Thread acceptThread;
    private ExecutorService clientPool;
    private volatile boolean running;

    public JsonRpcService(MinecraftServer server) {
        this(server, DEFAULT_PORT);
    }

    public JsonRpcService(MinecraftServer server, int port) {
        this.server = server;
        this.port = port;
    }

    /** 启动 TCP 监听（独立 accept 线程 + 每客户端线程池，不阻塞服务端主线程）。 */
    public void start() {
        if (running) {
            return;
        }
        running = true;
        clientPool = Executors.newCachedThreadPool(r -> {
            Thread t = new Thread(r, "PAL-JsonRpc-client");
            t.setDaemon(true);
            return t;
        });
        acceptThread = new Thread(this::listenLoop, "PAL-JsonRpc-accept");
        acceptThread.setDaemon(true);
        acceptThread.start();
        PeaceAndLove.LOGGER.info("[JSON-RPC] 服务已启动，监听端口 {}", port);
    }

    /** 停止服务。 */
    public void stop() {
        running = false;
        try {
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
        } catch (IOException e) {
            PeaceAndLove.LOGGER.warn("[JSON-RPC] 关闭 socket 异常", e);
        }
        if (acceptThread != null) {
            acceptThread.interrupt();
        }
        if (clientPool != null) {
            clientPool.shutdownNow();
        }
        PeaceAndLove.LOGGER.info("[JSON-RPC] 服务已停止");
    }

    private void listenLoop() {
        try (ServerSocket ss = new ServerSocket(port)) {
            this.serverSocket = ss;
            while (running) {
                try {
                    Socket client = ss.accept();
                    handleClient(client);
                } catch (IOException e) {
                    if (running) {
                        PeaceAndLove.LOGGER.warn("[JSON-RPC] 接受连接异常", e);
                    }
                }
            }
        } catch (IOException e) {
            if (running) {
                PeaceAndLove.LOGGER.error("[JSON-RPC] 无法绑定端口 {}", port, e);
            }
        }
    }

    private void handleClient(Socket client) {
        clientPool.submit(() -> {
            try (client;
                 BufferedReader in = new BufferedReader(new InputStreamReader(client.getInputStream()));
                 PrintWriter out = new PrintWriter(client.getOutputStream(), true)) {
                String line;
                while ((line = in.readLine()) != null) {
                    if (line.isBlank()) {
                        continue;
                    }
                    JsonObject response = handleRequest(line);
                    out.println(GSON.toJson(response));
                }
            } catch (IOException e) {
                PeaceAndLove.LOGGER.debug("[JSON-RPC] 客户端连接关闭", e);
            }
        });
    }

    private JsonObject handleRequest(String jsonLine) {
        JsonObject resp = new JsonObject();
        resp.addProperty("jsonrpc", "2.0");
        try {
            JsonObject req = JsonParser.parseString(jsonLine).getAsJsonObject();
            String method = req.get("method").getAsString();
            int id = req.has("id") ? req.get("id").getAsInt() : 0;
            resp.addProperty("id", id);

            JsonObject params = req.has("params") ? req.getAsJsonObject("params") : new JsonObject();
            Object result = dispatch(method, params);
            resp.add("result", GSON.toJsonTree(result));
        } catch (Exception e) {
            JsonObject error = new JsonObject();
            error.addProperty("code", -32603);
            error.addProperty("message", e.getMessage());
            resp.add("error", error);
        }
        return resp;
    }

    private Object dispatch(String method, JsonObject params) {
        return switch (method) {
            case "player.attack" -> playerAttack(params);
            case "player.move" -> playerMove(params);
            case "player.pos" -> playerPos();
            case "entity.list" -> entityList(params);
            case "server.status" -> serverStatus();
            case "verify.retaliation" -> verifyRetaliation(params);
            case "mob.anger" -> mobAnger(params);
            case "debug.inspect" -> debugInspect(params);
            case "pricing.scan" -> pricingScan();
            case "trade.probe" -> tradeProbe(params);
            default -> throw new IllegalArgumentException("未知方法: " + method);
        };
    }

    /**
     * 验证「被打反击」链路 —— 不依赖真实玩家。
     *
     * <p>流程：在出生点召唤一只僵尸 + 一只作为攻击者的骷髅，
     * 让骷髅 hurt 僵尸（走真实伤害管线，触发 setLastHurtByMob），
     * 等待 2 tick 让 targetSelector 评估 HurtByTargetGoal，
     * 回读僵尸 getTarget() 是否被设为骷髅。
     *
     * <p>攻击者用骷髅而非玩家：僵尸的 HurtByTargetGoal 构造时
     * toIgnoreDamage 为空，不会过滤同类/异类，任何 LivingEntity 攻击都触发。
     * 反击链的核心（HurtByTargetGoal.canUse → canAttack → canReach → setTarget）
     * 与攻击者身份无关——修复前 canReach 因 navigation 未激活返回 false，
     * 修复后攻击 Goal 保留、navigation 可用，canUse 应返回 true 并 setTarget。
     */
    private String verifyRetaliation(JsonObject params) {
        if (server == null) {
            return "错误: 服务端未就绪";
        }
        net.minecraft.server.level.ServerLevel level = server.overworld();
        net.minecraft.core.BlockPos spawn = level.getSharedSpawnPos();

        // 召唤僵尸（目标）与骷髅（攻击者）
        net.minecraft.world.entity.monster.Zombie zombie =
                new net.minecraft.world.entity.monster.Zombie(level);
        zombie.moveTo(spawn.getX() + 2, spawn.getY() + 1, spawn.getZ() + 2, 0, 0);
        level.addFreshEntity(zombie);

        net.minecraft.world.entity.monster.Skeleton skeleton =
                new net.minecraft.world.entity.monster.Skeleton(
                        net.minecraft.world.entity.EntityType.SKELETON, level);
        skeleton.moveTo(spawn.getX() + 5, spawn.getY() + 1, spawn.getZ() + 5, 0, 0);
        level.addFreshEntity(skeleton);

        // 用骷髅作为伤害来源打僵尸（真实伤害管线 → setLastHurtByMob）
        boolean hurtOk = zombie.hurt(level.damageSources().mobAttack(skeleton), 1.0F);

        // 等 2 tick 让 targetSelector 跑 HurtByTargetGoal.canUse()
        StringBuilder sb = new StringBuilder();
        sb.append("hurt 调用返回: ").append(hurtOk).append("\n");
        sb.append("lastHurtByMob: ").append(
                zombie.getLastHurtByMob() == null ? "null" : zombie.getLastHurtByMob().getType().toString()).append("\n");

        // 在服务端主线程调度延迟检查（2 tick ≈ 100ms）
        final boolean[] targetSet = new boolean[1];
        final String[] targetName = new String[1];
        server.execute(() -> {
            // 已过了 server.execute 的排队，直接再推 2 tick
            server.tell(new net.minecraft.server.TickTask(server.getTickCount() + 2, () -> {
                net.minecraft.world.entity.LivingEntity t = zombie.getTarget();
                targetSet[0] = (t == skeleton);
                targetName[0] = (t == null ? "null" : t.getType().toString());
                PeaceAndLove.LOGGER.info("[JSON-RPC] verify.retaliation 结果: target={}", targetName[0]);
            }));
        });

        // 同步等待最多 2 秒拿结果
        long deadline = System.currentTimeMillis() + 2000;
        while (System.currentTimeMillis() < deadline && targetName[0] == null) {
            try { Thread.sleep(50); } catch (InterruptedException ignored) { break; }
        }

        sb.append("反击判定 (2 tick 后 zombie.getTarget()): ")
                .append(targetName[0] == null ? "(超时未取到)" : targetName[0]).append("\n");
        sb.append(targetSet[0]
                ? "✅ 反击链正常: HurtByTargetGoal 成功 setTarget(攻击者)"
                : "❌ 反击未触发: getTarget() 未设为攻击者（仍不反击）");
        return sb.toString();
    }

    private String playerAttack(JsonObject params) {
        String targetType = params.has("target") ? params.get("target").getAsString() : "zombie";
        ServerPlayer player = getFirstPlayer();
        if (player == null) {
            return "错误: 无在线玩家";
        }
        // 找最近的指定类型生物
        List<Entity> entities = player.level().getEntities(player, player.getBoundingBox().inflate(32.0),
                e -> e instanceof Mob mob && mob.getType().toString().contains(targetType));
        if (entities.isEmpty()) {
            return "错误: 附近 32 格内无 " + targetType;
        }
        Entity target = entities.get(0);
        // 模拟玩家攻击：直接调用 hurt 并设置伤害来源为玩家
        target.hurt(player.damageSources().playerAttack(player), 1.0F);
        return "已攻击 " + target.getType().toString() + " (距离 " + String.format("%.1f", player.distanceTo(target)) + " 格)";
    }

    private String playerMove(JsonObject params) {
        double dx = params.has("dx") ? params.get("dx").getAsDouble() : 0;
        double dy = params.has("dy") ? params.get("dy").getAsDouble() : 0;
        double dz = params.has("dz") ? params.get("dz").getAsDouble() : 0;
        ServerPlayer player = getFirstPlayer();
        if (player == null) {
            return "错误: 无在线玩家";
        }
        player.setDeltaMovement(player.getDeltaMovement().add(dx, dy, dz));
        return "已施加移动向量 (" + dx + ", " + dy + ", " + dz + ")";
    }

    private String playerPos() {
        ServerPlayer player = getFirstPlayer();
        if (player == null) {
            return "错误: 无在线玩家";
        }
        return String.format("玩家 %s 位于 (%.1f, %.1f, %.1f) 维度 %s 模式 %s",
                player.getName().getString(),
                player.getX(), player.getY(), player.getZ(),
                player.level().dimension().location(),
                player.gameMode.getGameModeForPlayer().getName());
    }

    private String entityList(JsonObject params) {
        double radius = params.has("radius") ? params.get("radius").getAsDouble() : 16.0;
        ServerPlayer player = getFirstPlayer();
        if (player == null) {
            return "错误: 无在线玩家";
        }
        List<Entity> entities = player.level().getEntities(player, player.getBoundingBox().inflate(radius),
                e -> e instanceof Mob);
        StringBuilder sb = new StringBuilder("周围 " + radius + " 格内生物:\n");
        for (Entity e : entities) {
            sb.append(String.format("- %s (%.1f, %.1f, %.1f) 距离 %.1f 格\n",
                    e.getType().toString(), e.getX(), e.getY(), e.getZ(), player.distanceTo(e)));
        }
        return sb.toString();
    }

    /**
     * T-PRICE-001 真机探针：用数据包加载后的运行时战利品表扫描全部适配生物，
     * 返回每条掉落的 epk/countMax，供离线比对 spike 黄金基线 final_pricing_128.json。
     *
     * <p>必须走真机（而非单测 codec 解析）：enchanted_count_increase 等条件的
     * codec 依赖动态注册表 enchantment，纯 Bootstrap 单测构造不出 RegistryAccess；
     * 服务端 reloadableRegistries 已含全部数据包注册表，是唯一权威来源。
     */
    private Object pricingScan() {
        var registries = server.reloadableRegistries();
        top.windyvalley.peaceandlove.pricing.LootTableScanner scanner =
                new top.windyvalley.peaceandlove.pricing.LootTableScanner();
        top.windyvalley.peaceandlove.pricing.LootTableScanner.ScanResult result =
                scanner.scan(top.windyvalley.peaceandlove.scope.AdaptedMobs.ALL,
                        type -> registries.getLootTable(type.getDefaultLootTable()));

        java.util.List<java.util.Map<String, Object>> rows = new java.util.ArrayList<>();
        for (top.windyvalley.peaceandlove.pricing.LootTableScanner.DropEntry e : result.entries()) {
            java.util.Map<String, Object> row = new java.util.LinkedHashMap<>();
            row.put("entity", e.entityId().getPath());
            row.put("item", e.itemId().getPath());
            row.put("epk", e.epk());
            row.put("count_max", e.countMax());
            row.put("approximated", e.approximated());
            rows.add(row);
        }
        java.util.Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("scanned", top.windyvalley.peaceandlove.scope.AdaptedMobs.count());
        out.put("entries", result.entries().size());
        out.put("elapsed_ms", result.elapsedMillis());
        out.put("warnings", result.warnings());
        out.put("rows", rows);
        return out;
    }

    private String serverStatus() {
        return String.format("服务器在线，玩家数 %d，TPS 正常",
                server.getPlayerList().getPlayerCount());
    }

    /**
     * 按自定义名查询生物的 mod 仇恨归因 —— T-ANGER 真机验证探针。
     *
     * <p>为什么不能只看原版 {@code getTarget()}：守卫者等生物的攻击 Goal
     * （GuardianAttackGoal）每 tick 用视线校验目标，陆地隔间里会立刻
     * {@code setTarget(null)}，原版目标读不到；但 mod 的 AngerSource 标记
     * （PLAYER_DIRECT/KIN_ALERT）由本模组自管、保留 30s，不受原版 Goal 清目标影响。
     *
     * <p>params: {"name":"near"}。返回 {@code source=NONE|PLAYER_DIRECT|KIN_ALERT;
     * target=none|player|<type>;type=<id>}，找不到实体返回错误串。
     * 实体遍历必须在服务端主线程，RPC 线程同步等待最多 2s。
     */
    private String mobAnger(JsonObject params) {
        if (server == null) {
            return "错误: 服务端未就绪";
        }
        if (!params.has("name")) {
            return "错误: 缺少 name 参数";
        }
        String name = params.get("name").getAsString();
        java.util.concurrent.CompletableFuture<String> future = new java.util.concurrent.CompletableFuture<>();
        server.execute(() -> {
          try {
            Mob found = null;
            // 遍历所有维度（不能只看主世界）：地狱的 Brain 怪也要能查到，
            // 否则 mob.anger 在跨维度验证时永远“找不到生物”。
            for (ServerLevel level : server.getAllLevels()) {
                for (Entity e : level.getAllEntities()) {
                    if (e instanceof Mob mob && name.equals(mob.getName().getString())) {
                        found = mob;
                        break;
                    }
                }
                if (found != null) {
                    break;
                }
            }
            if (found == null) {
                future.complete("错误: 找不到名为 " + name + " 的生物");
                return;
            }
            String source = AngerController.angerSourceOf(found).name();
            net.minecraft.world.entity.LivingEntity t = found.getTarget();
            // Brain 怪目标在 ATTACK_TARGET 记忆里（getTarget 常为 null），
            // getTarget 读不到时回退到记忆，保证 target 字段对 Brain 怪也准确。
            if (t == null) {
                net.minecraft.world.entity.ai.memory.MemoryModuleType<?> atType =
                        net.minecraft.world.entity.ai.memory.MemoryModuleType.ATTACK_TARGET;
                // Goal 系生物（如僵尸）的 Brain 未注册 attack_target：直接 getMemory 会抛
                // IllegalStateException("Unregistered memory fetched")，让本查询任务挂掉。
                // hasMemoryValue 对「未注册」和「无值」都安全返回 false。
                if (found.getBrain().hasMemoryValue(atType)) {
                    Object mem = found.getBrain()
                            .getMemory((net.minecraft.world.entity.ai.memory.MemoryModuleType<Object>) atType)
                            .orElse(null);
                    if (mem instanceof net.minecraft.world.entity.LivingEntity le) {
                        t = le;
                    }
                }
            }
            String target;
            if (t == null) {
                target = "none";
            } else if (t instanceof net.minecraft.world.entity.player.Player) {
                target = "player";
            } else {
                target = net.minecraft.world.entity.EntityType.getKey(t.getType()).getPath();
            }
            future.complete("source=" + source + ";target=" + target
                    + ";type=" + net.minecraft.world.entity.EntityType.getKey(found.getType()).getPath());
          } catch (Exception ex) {
            // 兜底：任何查询期异常都要完成 future，否则外层只得到无信息的"超时 null"，掩盖真因
            future.complete("错误: 查询异常: " + ex.getClass().getSimpleName()
                    + ": " + ex.getMessage());
          }
        });
        try {
            return future.get(2, java.util.concurrent.TimeUnit.SECONDS);
        } catch (Exception e) {
            return "错误: 主线程查询超时: " + e.getMessage();
        }
    }

    /**
     * 真机诊断探针：按自定义名（name）或实体 id 路径（type）查一只 Mob，
     * 返回 {@code MobInspector} 采集的结构化门控/仇恨字段。本地单机无 RCON，
     * 命令 {@code /pal inspect} 的聊天回显读不到，采集正确性靠这里闭环断言。
     */
    private Object debugInspect(JsonObject params) {
        if (server == null) {
            return "错误: 服务端未就绪";
        }
        boolean byType = params.has("type");
        String key = byType
                ? params.get("type").getAsString()
                : (params.has("name") ? params.get("name").getAsString() : null);
        if (key == null) {
            return "错误: 需要 name 或 type 参数";
        }
        java.util.concurrent.CompletableFuture<Object> future = new java.util.concurrent.CompletableFuture<>();
        server.execute(() -> {
            try {
                Mob found = null;
                for (ServerLevel level : server.getAllLevels()) {
                    for (Entity e : level.getAllEntities()) {
                        if (!(e instanceof Mob mob)) {
                            continue;
                        }
                        boolean match = byType
                                ? net.minecraft.world.entity.EntityType.getKey(mob.getType())
                                        .getPath().equals(key)
                                : key.equals(mob.getName().getString());
                        if (match) {
                            found = mob;
                            break;
                        }
                    }
                    if (found != null) {
                        break;
                    }
                }
                if (found == null) {
                    future.complete("错误: 找不到 " + (byType ? "类型 " : "名为 ") + key + " 的生物");
                    return;
                }
                top.windyvalley.peaceandlove.debug.MobInspection info =
                        top.windyvalley.peaceandlove.debug.MobInspector.inspect(
                                found, PeaceAndLove.config().get());
                future.complete(info.toMap());
            } catch (Exception ex) {
                future.complete("错误: 查询异常: " + ex.getClass().getSimpleName() + ": " + ex.getMessage());
            }
        });
        try {
            return future.get(2, java.util.concurrent.TimeUnit.SECONDS);
        } catch (Exception e) {
            return "错误: 主线程查询超时: " + e.getMessage();
        }
    }

    /**
     * 交易链路探针（T-TRADE-003 真机定位）：读服务端一只命名怪的交易就绪状态。
     *
     * <p>params: {"name":"ttest","open":false}。返回结构化串：
     * merchant=实例是否实现了注入的 Merchant 接口；canTrade=门控；
     * angry=AngerController.isAngry；offers=getOffers().size()；
     * open=true 时额外直接调 setTradingPlayer+openTradingScreen（绕过 mobInteract
     * 注入，二分定位「是注入没触发」还是「开菜单本身失败」），回 openResult。
     */
    private String tradeProbe(JsonObject params) {
        if (server == null) {
            return "错误: 服务端未就绪";
        }
        if (!params.has("name")) {
            return "错误: 缺少 name 参数";
        }
        String name = params.get("name").getAsString();
        boolean doOpen = params.has("open") && params.get("open").getAsBoolean();
        java.util.concurrent.CompletableFuture<String> future = new java.util.concurrent.CompletableFuture<>();
        server.execute(() -> {
            try {
                Mob found = null;
                for (ServerLevel level : server.getAllLevels()) {
                    for (Entity e : level.getAllEntities()) {
                        if (e instanceof Mob mob && name.equals(mob.getName().getString())) {
                            found = mob;
                            break;
                        }
                    }
                    if (found != null) {
                        break;
                    }
                }
                if (found == null) {
                    future.complete("错误: 找不到名为 " + name + " 的生物");
                    return;
                }
                var cfg = PeaceAndLove.config().get();
                boolean merchant = found instanceof net.minecraft.world.item.trading.Merchant;
                boolean canTrade = top.windyvalley.peaceandlove.scope.NeutralizationScope
                        .canTrade(found.getType(), cfg);
                boolean angry = AngerController.isAngry(found);
                StringBuilder sb = new StringBuilder();
                sb.append("merchant=").append(merchant)
                        .append(";canTrade=").append(canTrade)
                        .append(";angry=").append(angry)
                        .append(";alive=").append(found.isAlive())
                        .append(";noai=").append(found.isNoAi());
                int n = -1;
                if (merchant) {
                    try {
                        net.minecraft.world.item.trading.Merchant m =
                                (net.minecraft.world.item.trading.Merchant) found;
                        net.minecraft.world.item.trading.MerchantOffers offers = m.getOffers();
                        n = offers.size();
                        // T-TRADE-004：stock="out" 置满全部报价（模拟买光，成交链路在 005）。
                        String stockAction = params.has("stock") ? params.get("stock").getAsString() : "";
                        if ("out".equals(stockAction)) {
                            for (var o : offers) {
                                o.setToOutOfStock();
                            }
                        }
                        // 回读每条 uses/maxUses/out 与世界时钟，供补货/持久化真机判定。
                        StringBuilder uses = new StringBuilder();
                        int idx = 0;
                        for (var o : offers) {
                            if (idx > 0) {
                                uses.append(",");
                            }
                            uses.append(o.getUses()).append("/").append(o.getMaxUses())
                                    .append(o.isOutOfStock() ? "X" : "");
                            idx++;
                        }
                        sb.append(";uses=").append(uses);
                        sb.append(";gameTime=").append(found.level().getGameTime());
                        sb.append(";dayTime=").append(found.level().getDayTime());
                        sb.append(";day=").append(found.level().getDayTime()
                                / RestockManager.DAY_TICKS);
                    } catch (Exception ex) {
                        sb.append(";offersError=").append(ex.getClass().getSimpleName());
                    }
                }
                sb.append(";offers=").append(n);
                if (doOpen && merchant) {
                    try {
                        ServerPlayer sp = getFirstPlayer();
                        if (sp == null) {
                            sb.append(";openResult=no_player");
                        } else {
                            net.minecraft.world.item.trading.Merchant m =
                                    (net.minecraft.world.item.trading.Merchant) found;
                            m.setTradingPlayer(sp);
                            m.openTradingScreen(sp, found.getDisplayName(), 0);
                            sb.append(";openResult=invoked");
                        }
                    } catch (Exception ex) {
                        sb.append(";openResult=EX:").append(ex.getClass().getSimpleName())
                                .append(":").append(ex.getMessage());
                    }
                }
                future.complete(sb.toString());
            } catch (Exception ex) {
                future.complete("错误: 查询异常: " + ex.getClass().getSimpleName() + ": " + ex.getMessage());
            }
        });
        try {
            return future.get(3, java.util.concurrent.TimeUnit.SECONDS);
        } catch (Exception e) {
            return "错误: 主线程查询超时: " + e.getMessage();
        }
    }

    private ServerPlayer getFirstPlayer() {
        List<ServerPlayer> players = server.getPlayerList().getPlayers();
        return players.isEmpty() ? null : players.get(0);
    }
}
