- [x] T-TEST-004: P2 验证：原版客户端交易

**完成备注：** 2026-10-13：第6条 Fabric 侧凭 1aef221 真机回填——fabric 版 mc-client-rpc 的 :fabric:runClient（零 PAL 类）连 Fabric 服，verify_fabric_trade_all 的单次成交首步即空手右键开窗+成交，与 NeoForge 同一边界；结论在 P1-P4-VERIFY.md。勘误：非官方启动器纯原版客户端
**优先级：** P0
**预估：** 3h
**Owner：** 人工 + agent
**依赖：** T-TRADE-003
**可并行：** T-TEST-001~003

## 目标

验证不装模组的原版客户端能否与装了模组的服务端正常交易。

## 来源

- 遗留：`../P1-P4-VERIFY.md` P2（design 阶段未完成）

## 验收标准

- [x] 启动装模组的 NeoForge 服务端
- [x] 用**零 PAL 类客户端**连接（勘误 2026-10-13：实测客户端为 mc-client-rpc 驱动客户端，仅开测试 JSON-RPC、不注册任何游戏内容/网络包/交易逻辑，`run/mods` 为空、零 peaceandlove 类；非官方启动器纯原版，但「玩家不装 PAL 即可交易」命题成立，边界见 P1-P4-VERIFY.md）
- [x] 右键僵尸能打开交易界面
- [x] 交易能正常完成，物品正确到手
- [x] 界面显示的价格与服务端一致
- [x] Fabric 侧同样验证一遍
- [x] 结论写入 `../P1-P4-VERIFY.md`（含定位结论「玩家客户端无需安装 PAL 即可交易」）；对外宣传文案落地归 T-REL-002/004（仓库仍私有，发版时再写）

## 技术要点

理论依据：`openTradingScreen` 是 `Merchant` 的 **default 方法**，
内部走原版 `MerchantMenu` + `ClientboundMerchantOffersPacket`，
全部是原版已有协议，客户端不需要模组代码即可解析。

**但未实测，不得提前写进宣传材料。**

验证方式：
```bash
./gradlew :neoforge:runServer      # 装模组的服务端
# 另开原版启动器 1.21.1，连 localhost:25565
```

⚠️ 若 P2 不成立，需补客户端模组，**影响发布定位文案**，
故本任务提前到 Sprint 3 而非发布阶段。

## 产出物

- 文档：更新 `../P1-P4-VERIFY.md` P2 章节
- Commit：`docs: 补充 P2 验证结论`

## 备注

⚠️ 风险任务：结论影响发布文案定位。
