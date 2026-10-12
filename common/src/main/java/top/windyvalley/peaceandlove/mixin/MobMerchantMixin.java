package top.windyvalley.peaceandlove.mixin;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.trading.Merchant;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.anger.AngerController;
import top.windyvalley.peaceandlove.config.PalConfig;
import top.windyvalley.peaceandlove.pricing.PriceTable;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;
import top.windyvalley.peaceandlove.trade.RestockManager;
import top.windyvalley.peaceandlove.trade.TradeInteraction;
import top.windyvalley.peaceandlove.trade.TradeOfferBuilder;

/**
 * 给 {@link Mob} 基类注入原版 {@link Merchant} 能力 —— ADR-002 方案 A。
 *
 * <p>P1 探针（spikes/p1-p3-probe）已在 Fabric / NeoForge 双端真机验证：
 * 注入成立、不需要 Access Transformer，{@code openTradingScreen} 的
 * default 实现可直接白嫖原版交易 GUI。本类是探针代码的正式化。
 *
 * <p><b>方法集以探针逐行核对为准</b>：实现 11 个方法（含 {@link #isClientSide()}），
 * 只白嫖 {@code canRestock()} 与 {@code openTradingScreen()} 两个 default。
 *
 * <p><b>成本边界</b>：{@link #getOffers()} 对不可交易生物（未适配 / 在白名单 /
 * 交易开关关 / Boss 未开 boss 开关）返回共享空列表，实例零分配；
 * 仅可交易生物首次访问时懒加载。
 *
 * <p>⚠️ Mixin 类加载约束：普通代码不得直接引用本类，需要 Merchant 视图时
 * 直接把 Mob 当 {@link Merchant} 用（接口由本 Mixin 运行时织入）。
 */
@Mixin(Mob.class)
public abstract class MobMerchantMixin implements Merchant {

    /** 非交易目标共享的不可变空报价表 —— 任何调用方都不得往里 add。 */
    @Unique
    private static final MerchantOffers pal$EMPTY = new MerchantOffers();

    @Unique
    private Player pal$tradingPlayer;

    @Unique
    private MerchantOffers pal$offers;

    /** 当前 pal$offers 的内容签名 = PriceTable 指纹 + max_uses_per_day；任一变化则重建（改价或改限购）。 */
    @Unique
    private long pal$offersSig;

    /** 上次补货的世界时刻（level.getGameTime，单调）；-1=尚未锚定。持久化以支持离线补算。 */
    @Unique
    private long pal$lastRestockGame = -1L;

    /** 上次补货所在自然日（level.getDayTime()/24000）；睡觉快进 getDayTime 据此触发补货。 */
    @Unique
    private long pal$lastRestockDay;

    @Override
    public void setTradingPlayer(Player player) {
        this.pal$tradingPlayer = player;
    }

    @Override
    public Player getTradingPlayer() {
        return this.pal$tradingPlayer;
    }

    @Override
    public MerchantOffers getOffers() {
        Mob self = (Mob) (Object) this;
        // 客户端侧拿不到服务端配置，且客户端只在交易 GUI 已打开时才读报价；
        // 报价由服务端菜单同步，客户端 Mob 自身懒初始化无意义。
        if (self.level().isClientSide) {
            return pal$offers == null ? pal$EMPTY : pal$offers;
        }
        PalConfig cfg = PeaceAndLove.config().get();
        if (!NeutralizationScope.canTrade(self.getType(), cfg)) {
            return pal$EMPTY;
        }
        PriceTable table = PeaceAndLove.priceTable().table();
        long sig = offerSignature(table.fingerprint(), cfg.max_uses_per_day());
        // T-TRADE-003/004：
        //  - 首次（无内存报价且无存档报价）：组装并锚定补货时刻；
        //  - 签名一致（含从存档恢复、reload 未改价/限购）：复用，保留购买次数 uses；
        //  - 签名变化（改价/改锚点/改掉落量/改限购后 reload）：重建，uses 归零（旧报价已失效）。
        if (pal$offers == null || pal$offersSig != sig) {
            this.pal$offers = TradeOfferBuilder.assemble(self.getType(), cfg, table);
            this.pal$offersSig = sig;
            if (this.pal$lastRestockGame < 0L) {
                this.pal$lastRestockGame = self.level().getGameTime();
                this.pal$lastRestockDay = self.level().getDayTime() / RestockManager.DAY_TICKS;
            }
        }
        return this.pal$offers;
    }

    /** 报价内容签名：定价指纹与限购次数任一变化即失效。 */
    @Unique
    private static long offerSignature(long priceFingerprint, int maxUses) {
        return priceFingerprint * 31L + maxUses;
    }

    @Override
    public void overrideOffers(MerchantOffers offers) {
        this.pal$offers = offers;
    }

    @Override
    public void notifyTrade(MerchantOffer offer) {
        offer.increaseUses();
    }

    @Override
    public void notifyTradeUpdated(ItemStack stack) {
        // 怪物商人不做村民那套需求量反馈
    }

    @Override
    public int getVillagerXp() {
        return 0;
    }

    @Override
    public void overrideXp(int xp) {
        // 无经验条
    }

    @Override
    public boolean showProgressBar() {
        return false;
    }

    @Override
    public SoundEvent getNotifyTradeSound() {
        return SoundEvents.VILLAGER_YES;
    }

    @Override
    public boolean isClientSide() {
        return ((Mob) (Object) this).level().isClientSide;
    }

    /**
     * 右键交互 → 打开原版交易 GUI（T-TRADE-003）。
     *
     * <p><b>服务端权威，客户端不干预。</b>门控真值表在
     * {@link TradeInteraction#evaluate} 纯逻辑里单测覆盖，Mixin 只抽取事实：
     * <ul>
     *   <li>客户端物理端没有服务端配置/仇恨/报价（Brain 记忆与 AngerController
     *       状态都不同步），在这里猜门控只会对村民等未适配实体产生错误的 SUCCESS
     *       预测；故客户端直接放行（保持原版 PASS），开界面完全由服务端
     *       openTradingScreen 的 openMenu + 报价同步包驱动 —— 不依赖客户端返回值；</li>
     *   <li>服务端不满足条件（未适配/白名单/开关关/Boss 开关关/仇恨中/死亡/
     *       已在交易/手持物品）→ 不注入返回值，保持原版交互；</li>
     *   <li>条件满足但无报价 → 吞掉交互不开界面（村民「没货」同款 CONSUME）；</li>
     *   <li>有报价 → {@code setTradingPlayer + openTradingScreen}（default 实现走
     *       MerchantMenu + ClientboundMerchantOffersPacket），返回 CONSUME。</li>
     * </ul>
     *
     * <p>客户端对同一次右键会先发 interactAt 再发 interact 两个包，服务端都汇到
     * 本方法；{@code getTradingPlayer()!=null} 守卫与村民 isTrading() 同义，
     * 防止同一 tick 重复 openMenu。
     */
    @Inject(method = "mobInteract", at = @At("HEAD"), cancellable = true)
    private void pal$onMobInteract(Player player, InteractionHand hand,
                                   CallbackInfoReturnable<InteractionResult> cir) {
        Mob self = (Mob) (Object) this;
        // 客户端不干预：不猜服务端状态，保持原版 PASS（连村民等未适配实体也零影响）。
        if (self.level().isClientSide) {
            return;
        }
        boolean bothHandsEmpty = player.getItemInHand(InteractionHand.MAIN_HAND).isEmpty()
                && player.getItemInHand(InteractionHand.OFF_HAND).isEmpty();
        TradeInteraction.Decision decision = TradeInteraction.evaluate(
                NeutralizationScope.canTrade(self.getType(), PeaceAndLove.config().get()),
                AngerController.isAngry(self),
                self.isAlive(),
                getTradingPlayer() == null,
                bothHandsEmpty,
                !getOffers().isEmpty());
        if (decision == TradeInteraction.Decision.FALL_THROUGH) {
            return;
        }
        if (hand == InteractionHand.MAIN_HAND && decision == TradeInteraction.Decision.OPEN) {
            setTradingPlayer(player);
            openTradingScreen(player, self.getDisplayName(), 0);
        }
        cir.setReturnValue(InteractionResult.CONSUME);
    }

    /**
     * 每 tick 补货判定（T-TRADE-004，对齐村民双时钟模型）。
     *
     * <p>只对<b>已持有报价</b>的生物生效（被右键过，或从存档恢复了购买状态）。
     * 判定是纯算术 {@link RestockManager#evaluate}：单调 gameTime 的滚动间隔 OR
     * getDayTime 的跨自然日（睡觉快进这条腿），且要求至少一条报价售罄（needsToRestock），
     * 没买光就不补、锚点不推进。区块卸载期间不 tick，重挂后首 tick 用两个时钟一次性补算。
     */
    @Inject(method = "tick", at = @At("HEAD"))
    private void pal$onTick(CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        if (self.level().isClientSide || pal$offers == null || pal$offers.isEmpty()) {
            return;
        }
        RestockManager.RestockResult r = RestockManager.evaluate(
                self.level().getGameTime(),
                self.level().getDayTime(),
                pal$lastRestockGame,
                pal$lastRestockDay,
                PeaceAndLove.config().get().restock_interval_days(),
                RestockManager.anyOutOfStock(pal$offers));
        if (r.restocked()) {
            RestockManager.resetUses(pal$offers);
        }
        pal$lastRestockGame = r.newLastGame();
        pal$lastRestockDay = r.newLastDay();
    }

    /**
     * 持久化购买次数与补货节奏（T-TRADE-004）。
     *
     * <p>只写已组装报价的怪（{@code pal$offers != null}），不给未交易过的野生怪塞 NBT。
     * 存报价是为了让 maxUses/uses 跨区块卸载/重启保留——否则玩家走远再回来就能无视限购。
     * 同时存内容签名，读回后若配置已改价/改限购，{@link #getOffers()} 会按新签名重建。
     */
    @Inject(method = "addAdditionalSaveData", at = @At("TAIL"))
    private void pal$save(CompoundTag tag, CallbackInfo ci) {
        if (pal$offers == null) {
            return;
        }
        tag.putLong("pal_sig", pal$offersSig);
        tag.putLong("pal_restock_game", pal$lastRestockGame);
        tag.putLong("pal_restock_day", pal$lastRestockDay);
        tag.put("pal_offers", MerchantOffers.CODEC.encodeStart(
                ((Mob) (Object) this).registryAccess().createSerializationContext(NbtOps.INSTANCE),
                pal$offers).getOrThrow());
    }

    /** 读回购买状态；签名校验交给 {@link #getOffers()}（配置变更则重建，uses 归零）。 */
    @Inject(method = "readAdditionalSaveData", at = @At("TAIL"))
    private void pal$load(CompoundTag tag, CallbackInfo ci) {
        if (!tag.contains("pal_offers")) {
            return;
        }
        MerchantOffers.CODEC.parse(
                ((Mob) (Object) this).registryAccess().createSerializationContext(NbtOps.INSTANCE),
                tag.get("pal_offers")
        ).result().ifPresent(loaded -> {
            this.pal$offers = loaded;
            this.pal$offersSig = tag.getLong("pal_sig");
            this.pal$lastRestockGame = tag.contains("pal_restock_game")
                    ? tag.getLong("pal_restock_game") : -1L;
            this.pal$lastRestockDay = tag.contains("pal_restock_day")
                    ? tag.getLong("pal_restock_day") : 0L;
        });
    }

    // canRestock() 与 openTradingScreen() 有 default 实现，不覆写。
}
