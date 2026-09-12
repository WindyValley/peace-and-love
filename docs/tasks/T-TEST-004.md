# T-TEST-004: P2 验证：原版客户端交易

**状态：** todo
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

- [ ] 启动装模组的 NeoForge 服务端
- [ ] 用**原版 1.21.1 客户端**连接（不装任何模组）
- [ ] 右键僵尸能打开交易界面
- [ ] 交易能正常完成，物品正确到手
- [ ] 界面显示的价格与服务端一致
- [ ] Fabric 侧同样验证一遍
- [ ] 结论写入 `../P1-P4-VERIFY.md` 并更新宣传文案定位

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
