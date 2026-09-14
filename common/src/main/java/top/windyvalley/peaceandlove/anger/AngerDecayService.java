package top.windyvalley.peaceandlove.anger;

import dev.architectury.event.events.common.TickEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import top.windyvalley.peaceandlove.PeaceAndLove;

/**
 * 仇恨衰减服务 —— T-ANGER-004。每 tick 对已仇恨的 Goal 系生物做脱战判定。
 *
 * <p>脱战条件（满足其一）：仇恨计时结束，或玩家脱离配置距离（默认 32 格）。
 * 脱战后调 {@link AngerController#calmDown} 恢复中立，可重新交易。
 *
 * <p><b>只遍历 Goal 系</b>：NeutralMob 系（末影人/猪灵等）由原版 persistentAnger
 * 计时自管冷却，无需这里干预。本服务对 Goal 系（僵尸/骷髅等 32 个）递减
 * AngerController 自维护的仇恨计时。
 *
 * <p><b>性能</b>：遍历 level 全部实体但早退——非 Mob、非 Goal 系、非仇恨状态
 * 的立即 continue，实际进 tickDecay 逻辑的只有「已仇恨的 Goal 系生物」，
 * 数量极少（通常 0~几只）。与 NeutralizationService 的 Brain 系遍历同理。
 */
public final class AngerDecayService {

    /** 接线：注册服务端 tick 钩子。由 PeaceAndLove.init 调用一次。 */
    public void register() {
        TickEvent.SERVER_LEVEL_POST.register(this::onLevelTick);
        PeaceAndLove.LOGGER.info("仇恨衰减服务已接线（SERVER_LEVEL_POST）");
    }

    private void onLevelTick(ServerLevel level) {
        for (Entity entity : level.getAllEntities()) {
            if (!(entity instanceof Mob mob)) {
                continue;
            }
            // 只处理「当前处于仇恨状态」的 Goal 系生物；
            // NeutralMob 系、中立生物在 tickDecay 内部早退
            AngerController.tickDecay(mob);
        }
    }
}
