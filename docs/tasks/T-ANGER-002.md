# T-ANGER-002: AngerController 状态机与单目标锁定

**状态：** todo
**优先级：** P0
**预估：** 5h
**Owner：** agent
**依赖：** T-ANGER-001
**可并行：** T-NEUT-004

## 目标

实现仇恨状态机，仇恨**锁定攻击者本人**，不扩散到其他玩家或 NPC。

## 来源

- 设计：`../02-design.md` §3.6 仇恨控制
- 需求：FR-1.2

## 验收标准

- [ ] 仇恨目标为**单个 UUID**（攻击者本人）
- [ ] 玩家 A 攻击 → 生物只追 A，**不攻击旁边的玩家 B**
- [ ] 仇恨期间不开交易界面
- [ ] 仇恨期间恢复原版攻击 Goal（能反击）
- [ ] 脱战后清除仇恨，恢复中立可交易
- [ ] 多人场景：A 交易中 B 攻击 → 强制关闭 A 的界面并**退回绿宝石**
- [ ] 状态持久化到 NBT（重登不丢仇恨）

## 技术要点

复用原版 `NeutralMob.persistentAngerTarget`（单个 UUID，语义天然吻合）。
末影人与僵尸猪灵已实现该接口的 5 个方法，**可直接复用存储层**。

⚠️ **绿宝石退回**：玩家 A 正在交易界面中，B 攻击导致生物转敌对，
服务端强制关闭 A 的 `MerchantMenu`，此时 A 放在输入槽的绿宝石必须退回背包，
否则物品丢失。用 `MerchantMenu#removed()` 的原版逻辑处理。

## 产出物

- 代码：`anger/AngerController.java`
- 测试：`AngerControllerTest.java`
- Commit：`feat(anger): 实现仇恨状态机与单目标锁定`

## 备注

无
