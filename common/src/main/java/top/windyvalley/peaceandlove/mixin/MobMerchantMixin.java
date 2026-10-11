package top.windyvalley.peaceandlove.mixin;

import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.trading.Merchant;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import top.windyvalley.peaceandlove.PeaceAndLove;
import top.windyvalley.peaceandlove.scope.NeutralizationScope;

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

    /** 上次补货所在的游戏日（day time / 24000）；补货逻辑在后续 T-TRADE 任务接入。 */
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
        if (this.pal$offers == null) {
            Mob self = (Mob) (Object) this;
            // 客户端侧拿不到服务端配置，且客户端只在交易 GUI 已打开时才读报价；
            // 报价由服务端菜单同步，客户端 Mob 自身懒初始化无意义。
            if (self.level().isClientSide) {
                return pal$EMPTY;
            }
            if (!NeutralizationScope.canTrade(self.getType(), PeaceAndLove.config().get())) {
                return pal$EMPTY;
            }
            this.pal$offers = new MerchantOffers();
        }
        return this.pal$offers;
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

    // canRestock() 与 openTradingScreen() 有 default 实现，不覆写。
}
