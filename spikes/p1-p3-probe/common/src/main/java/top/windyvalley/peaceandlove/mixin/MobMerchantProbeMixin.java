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

/**
 * P1 探针 —— 验证「Mixin 给 Mob 注入 Merchant 接口」是否在 Fabric / NeoForge 双端可行。
 *
 * 这是 ADR-002 方案 A 的核心机制。若 NeoForge 侧需要 Access Transformer，
 * 编译或运行时会暴露出来。
 *
 * ★ Merchant 接口的真实构成（1.21.1 官方 mappings 逐行核对）：
 *     10 个 abstract：
 *       setTradingPlayer, getTradingPlayer, getOffers, overrideOffers,
 *       notifyTrade, notifyTradeUpdated, getVillagerXp, overrideXp,
 *       showProgressBar, getNotifyTradeSound, isClientSide
 *      2 个 default：
 *       canRestock()          —— 无需覆写
 *       openTradingScreen()   —— ★ 原版已实现，GUI 白得
 *
 * 注：早先 extract_api.py 因常量池反查歧义漏报了 overrideOffers / notifyTrade /
 *     overrideXp / openTradingScreen，此处以 mappings 原文为准。
 */
@Mixin(Mob.class)
public abstract class MobMerchantProbeMixin implements Merchant {

    @Unique
    private Player pal$tradingPlayer;

    @Unique
    private MerchantOffers pal$offers = new MerchantOffers();

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
    }

    @Override
    public int getVillagerXp() {
        return 0;
    }

    @Override
    public void overrideXp(int xp) {
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

    // canRestock() 与 openTradingScreen() 有 default 实现，无需覆写
}
